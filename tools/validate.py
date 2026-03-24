#!/usr/bin/env python3
"""
validate.py — Validate an AgentCommons dataset before submission.

Checks metadata completeness, record count accuracy, and runs a
basic PII pattern scan on memory content.

Usage:
  python validate.py --dataset ./my-dataset
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path

REQUIRED_METADATA_FIELDS = [
    "name", "version", "embedding_model", "topic_tags",
    "agent_type", "record_count", "language",
    "submitted_by", "submitted_at", "provenance", "description"
]

SUPPORTED_EMBEDDING_MODELS = [
    "nomic-embed-text",
    # Add others as the community standardizes on them
]

# Basic PII patterns — not exhaustive, a starting point
PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email address"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",                    "phone number"),
    (r"\b\d{3}-\d{2}-\d{4}\b",                                 "SSN pattern"),
    (r"(?i)\b(password|passwd|secret|token|api[-_]?key)\s*[=:]\s*\S+", "credential pattern"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b",                          "IP address"),
]

BLOCKED_TAGS = {"personality", "relationship", "style", "personal", "private"}


def validate(dataset_path: Path) -> bool:
    errors = []
    warnings = []

    print(f"Validating: {dataset_path}\n")

    # Check required files exist
    metadata_file = dataset_path / "metadata.json"
    db_file       = dataset_path / "knowledge.db"
    readme_file   = dataset_path / "README.md"

    for f in [metadata_file, db_file, readme_file]:
        if not f.exists():
            errors.append(f"Missing required file: {f.name}")

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        return False

    # Validate metadata
    try:
        metadata = json.loads(metadata_file.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"metadata.json is not valid JSON: {e}")
        for e in errors:
            print(f"  ERROR: {e}")
        return False

    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata:
            errors.append(f"metadata.json missing required field: '{field}'")
        elif metadata[field] in ("", [], "your-github-username", "YYYY-MM-DD",
                                 "Describe what domain knowledge this dataset contains and how it was generated."):
            errors.append(f"metadata.json field '{field}' appears to be unfilled template value")

    if metadata.get("embedding_model") not in SUPPORTED_EMBEDDING_MODELS:
        warnings.append(
            f"embedding_model '{metadata.get('embedding_model')}' is not in the known list. "
            f"Supported: {', '.join(SUPPORTED_EMBEDDING_MODELS)}. "
            f"Non-standard models are allowed but limit compatibility."
        )

    # Validate record count matches database
    try:
        conn = sqlite3.connect(db_file)
        actual_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()

        declared_count = metadata.get("record_count", 0)
        if actual_count != declared_count:
            errors.append(
                f"record_count mismatch: metadata says {declared_count}, database has {actual_count}"
            )
        else:
            print(f"  ✓ Record count: {actual_count}")
    except Exception as e:
        errors.append(f"Could not read knowledge.db: {e}")

    # Check for blocked tags in the database
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, tags FROM memories").fetchall()
        conn.close()

        blocked_found = []
        for row in rows:
            tags = set(json.loads(row["tags"]))
            blocked = tags & BLOCKED_TAGS
            if blocked:
                blocked_found.append((row["id"], blocked))

        if blocked_found:
            for mid, btags in blocked_found:
                errors.append(f"Memory '{mid}' contains blocked tags: {btags} — personal memories must not be exported")
        else:
            print(f"  ✓ No blocked tags found")
    except Exception as e:
        errors.append(f"Could not scan tags: {e}")

    # PII scan
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

    # Check README is not the template
    readme_content = readme_file.read_text()
    if "Fill in dataset description" in readme_content or "Describe the domain knowledge" in readme_content:
        warnings.append("README.md appears to contain unfilled template text")
    else:
        print(f"  ✓ README.md present")

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

    print("Validation PASSED — dataset is ready for submission.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate an AgentCommons dataset before submission.")
    parser.add_argument("--dataset", required=True, help="Path to the dataset folder")
    args = parser.parse_args()
    validate(Path(args.dataset))


if __name__ == "__main__":
    main()
