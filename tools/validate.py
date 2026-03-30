#!/usr/bin/env python3
"""
validate.py — Validate an AgentCommons dataset against the AC-1 specification.

Checks file structure, metadata completeness, schema conformance, content
bounds, tag formatting, embedding consistency, PII patterns, and size limits.

Usage:
  python validate.py --dataset ./my-dataset
"""

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path

SPEC_VERSION = "AC-1.0"

REQUIRED_METADATA_FIELDS = [
    "name", "version", "embedding_model", "topic_tags",
    "agent_type", "record_count", "language",
    "submitted_by", "submitted_at", "provenance", "description"
]

SUPPORTED_EMBEDDING_MODELS = [
    "nomic-embed-text",
    # Add others as the community standardizes on them
]

REQUIRED_COLUMNS = {"id", "content", "embedding", "tags", "source_at"}

# Basic PII patterns — not exhaustive, a starting point
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email address"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",                    "phone number"),
    (r"\b\d{3}-\d{2}-\d{4}\b",                                 "SSN pattern"),
    (r"(?i)\b(password|passwd|secret|token|api[-_]?key)\s*[=:]\s*\S+", "credential pattern"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b",                          "IP address"),
]

BLOCKED_TAGS = {"personality", "relationship", "style", "personal", "private", "preferences", "feedback", "decision"}

TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

MAX_DATASET_SIZE_MB = 50
MIN_CONTENT_LENGTH = 20
MAX_CONTENT_LENGTH = 10000
MAX_TAGS_PER_MEMORY = 5
MAX_TAG_LENGTH = 32


def validate(dataset_path: Path) -> bool:
    errors = []
    warnings = []

    print(f"Validating: {dataset_path}")
    print(f"Spec: {SPEC_VERSION}\n")

    # --- File structure ---
    metadata_file = dataset_path / "metadata.json"
    db_file       = dataset_path / "knowledge.db"
    readme_file   = dataset_path / "README.md"

    for f in [metadata_file, db_file, readme_file]:
        if not f.exists():
            errors.append(f"Missing required file: {f.name}")

    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        return False

    # --- Dataset size ---
    total_size = sum(f.stat().st_size for f in dataset_path.iterdir() if f.is_file())
    total_size_mb = total_size / (1024 * 1024)
    if total_size_mb > MAX_DATASET_SIZE_MB:
        errors.append(f"Dataset size {total_size_mb:.1f} MB exceeds {MAX_DATASET_SIZE_MB} MB limit")
    else:
        print(f"  ✓ Dataset size: {total_size_mb:.2f} MB")

    # --- Directory name ---
    dir_name = dataset_path.name
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", dir_name):
        errors.append(f"Directory name '{dir_name}' must be lowercase alphanumeric with hyphens only")

    # --- Metadata ---
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"metadata.json is not valid JSON: {e}")
        for e in errors:
            print(f"  ✗ {e}")
        return False

    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata:
            errors.append(f"metadata.json missing required field: '{field}'")
        elif metadata[field] in ("", [], "your-github-username", "YYYY-MM-DD",
                                 "Describe what domain knowledge this dataset contains and how it was generated.",
                                 "your-dataset-name"):
            errors.append(f"metadata.json field '{field}' appears to be unfilled template value")

    # Directory name must match metadata name
    meta_name = metadata.get("name", "")
    if meta_name and meta_name != dir_name:
        errors.append(f"Directory name '{dir_name}' does not match metadata name '{meta_name}'")

    if metadata.get("embedding_model") not in SUPPORTED_EMBEDDING_MODELS:
        warnings.append(
            f"embedding_model '{metadata.get('embedding_model')}' is not in the known list. "
            f"Supported: {', '.join(SUPPORTED_EMBEDDING_MODELS)}. "
            f"Non-standard models are allowed but limit compatibility."
        )

    # Spec version check (SHOULD level — warn, don't block)
    if "spec_version" not in metadata:
        warnings.append(f"metadata.json missing 'spec_version' field (recommended: \"{SPEC_VERSION}\")")
    elif metadata["spec_version"] != SPEC_VERSION:
        warnings.append(f"spec_version is '{metadata['spec_version']}', expected '{SPEC_VERSION}'")

    # --- Schema validation ---
    try:
        conn = sqlite3.connect(db_file)

        # Check for extra tables
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]
        if tables != ["memories"]:
            if "memories" not in tables:
                errors.append("Database missing required 'memories' table")
            extra = [t for t in tables if t != "memories"]
            if extra:
                errors.append(f"Database contains extra tables: {', '.join(extra)}")

        # Check columns
        if "memories" in tables:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)").fetchall()}
            missing_cols = REQUIRED_COLUMNS - columns
            extra_cols = columns - REQUIRED_COLUMNS
            if missing_cols:
                errors.append(f"memories table missing columns: {', '.join(sorted(missing_cols))}")
            if extra_cols:
                errors.append(f"memories table has extra columns (strip before submitting): {', '.join(sorted(extra_cols))}")
            if not missing_cols and not extra_cols:
                print(f"  ✓ Schema matches AC-1")

        conn.close()
    except Exception as e:
        errors.append(f"Could not read knowledge.db schema: {e}")

    # --- Record count ---
    try:
        conn = sqlite3.connect(db_file)
        actual_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()

        declared_count = metadata.get("record_count", 0)
        if actual_count != declared_count:
            errors.append(f"record_count mismatch: metadata says {declared_count}, database has {actual_count}")
        else:
            print(f"  ✓ Record count: {actual_count}")
    except Exception as e:
        errors.append(f"Could not read knowledge.db: {e}")

    # --- Content, tags, and embeddings (single pass) ---
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, content, tags, embedding FROM memories").fetchall()
        conn.close()

        content_errors = []
        tag_errors = []
        blocked_found = []
        embedding_dims = set()

        for row in rows:
            mid = row["id"]
            content = row["content"]
            raw_tags = row["tags"]
            raw_embedding = row["embedding"]

            # Content length
            if content is None or content.strip() == "":
                content_errors.append(f"Memory '{mid}': content is empty or whitespace-only")
            elif len(content) < MIN_CONTENT_LENGTH:
                content_errors.append(f"Memory '{mid}': content is {len(content)} chars (minimum {MIN_CONTENT_LENGTH})")
            elif len(content) > MAX_CONTENT_LENGTH:
                content_errors.append(f"Memory '{mid}': content is {len(content)} chars (maximum {MAX_CONTENT_LENGTH})")

            # Tags
            try:
                tags = json.loads(raw_tags)
                if not isinstance(tags, list):
                    tag_errors.append(f"Memory '{mid}': tags is not a JSON array")
                    continue

                if len(tags) < 1:
                    tag_errors.append(f"Memory '{mid}': must have at least 1 tag")
                elif len(tags) > MAX_TAGS_PER_MEMORY:
                    tag_errors.append(f"Memory '{mid}': has {len(tags)} tags (maximum {MAX_TAGS_PER_MEMORY})")

                for tag in tags:
                    if not isinstance(tag, str):
                        tag_errors.append(f"Memory '{mid}': tag {tag!r} is not a string")
                    elif len(tag) > MAX_TAG_LENGTH:
                        tag_errors.append(f"Memory '{mid}': tag '{tag}' exceeds {MAX_TAG_LENGTH} chars")
                    elif not TAG_PATTERN.match(tag):
                        tag_errors.append(f"Memory '{mid}': tag '{tag}' must be lowercase alphanumeric with hyphens")

                blocked = set(tags) & BLOCKED_TAGS
                if blocked:
                    blocked_found.append((mid, blocked))

            except json.JSONDecodeError:
                tag_errors.append(f"Memory '{mid}': tags is not valid JSON")

            # Embedding dimensionality
            try:
                embedding = json.loads(raw_embedding)
                if isinstance(embedding, list) and len(embedding) > 0:
                    embedding_dims.add(len(embedding))
            except (json.JSONDecodeError, TypeError):
                content_errors.append(f"Memory '{mid}': embedding is not a valid JSON array")

        # Report content
        if content_errors:
            for ce in content_errors:
                errors.append(ce)
        else:
            print(f"  ✓ Content length: all records within bounds ({MIN_CONTENT_LENGTH}-{MAX_CONTENT_LENGTH} chars)")

        # Report tags
        if tag_errors:
            for te in tag_errors:
                errors.append(te)
        else:
            print(f"  ✓ Tag format: all records compliant")

        if blocked_found:
            for mid, btags in blocked_found:
                errors.append(f"Memory '{mid}' contains blocked tags: {btags}")
        else:
            print(f"  ✓ No blocked tags found")

        # Report embedding consistency
        if len(embedding_dims) > 1:
            errors.append(f"Inconsistent embedding dimensions across records: {sorted(embedding_dims)}")
        elif len(embedding_dims) == 1:
            dim = embedding_dims.pop()
            print(f"  ✓ Embedding dimensions: {dim} (consistent)")

    except Exception as e:
        errors.append(f"Could not scan records: {e}")

    # --- PII scan ---
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, content FROM memories").fetchall()
        conn.close()

        pii_hits = []
        for row in rows:
            for pattern, label in PII_PATTERNS:
                if re.search(pattern, row["content"]):
                    pii_hits.append((row["id"], label))

        if pii_hits:
            for mid, label in pii_hits:
                warnings.append(f"Possible {label} detected in memory '{mid}' — review before submitting")
        else:
            print(f"  ✓ No PII patterns detected")
    except Exception as e:
        warnings.append(f"PII scan could not complete: {e}")

    # --- README ---
    readme_content = readme_file.read_text(encoding="utf-8")
    if "Fill in dataset description" in readme_content or "Describe the domain knowledge" in readme_content:
        warnings.append("README.md appears to contain unfilled template text")
    elif len(readme_content.strip()) < 50:
        warnings.append("README.md appears too short — add a meaningful description")
    else:
        print(f"  ✓ README.md present")

    # --- Results ---
    print()

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  ⚠  {w}")
        print()

    if errors:
        print("Errors:")
        for e in errors:
            print(f"  ✗  {e}")
        print()
        print("Validation FAILED — fix the errors above before submitting.")
        return False

    print(f"Validation PASSED ({SPEC_VERSION}) — dataset is ready for submission.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate an AgentCommons dataset against the AC-1 spec.")
    parser.add_argument("--dataset", required=True, help="Path to the dataset folder")
    args = parser.parse_args()
    success = validate(Path(args.dataset))
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
