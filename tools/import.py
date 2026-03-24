#!/usr/bin/env python3
"""
import.py — Import an AgentCommons dataset into your MCP Memory Server database.

Supports four merge strategies: union, dedup, federated, and distillation.

Usage:
  python import.py --dataset community/cloudflare/cloudflare-workers-patterns --db ./memory.db
  python import.py --dataset community/cloudflare/cloudflare-workers-patterns --db ./memory.db --merge dedup
  python import.py --dataset community/cloudflare/cloudflare-workers-patterns --db ./memory.db --merge dedup --re-embed --embed-model nomic-embed-text
"""

import argparse
import json
import secrets
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


AGENTCOMMONS_ROOT = Path(__file__).parent.parent
OLLAMA_URL = "http://localhost:11434"


def get_embedding(text: str, model: str) -> list[float]:
    payload = json.dumps({"model": model, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(x ** 2 for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def load_dataset(dataset_path: Path):
    """Load records from a dataset's knowledge.db."""
    db = dataset_path / "knowledge.db"
    metadata_file = dataset_path / "metadata.json"

    if not db.exists():
        raise FileNotFoundError(f"knowledge.db not found in {dataset_path}")

    metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM memories").fetchall()
    conn.close()
    return rows, metadata


def resolve_dataset_path(dataset_arg: str) -> Path:
    """Resolve dataset path — either absolute or relative to agentcommons root."""
    p = Path(dataset_arg)
    if p.exists():
        return p
    relative = AGENTCOMMONS_ROOT / dataset_arg
    if relative.exists():
        return relative
    raise FileNotFoundError(f"Dataset not found: {dataset_arg}")


def get_target_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def merge_union(records, target_conn, embed_model: str, re_embed: bool, scope: str, agent_id: str, team_id: str):
    imported = 0
    for row in records:
        embedding = get_embedding(row["content"], embed_model) if re_embed else json.loads(row["embedding"])
        new_id = secrets.token_hex(8)
        try:
            target_conn.execute(
                """INSERT INTO memories (id, agent_id, team_id, scope, content, embedding, tags, created_at, conflict_ids, resolved)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', 0)""",
                (new_id, agent_id, team_id, scope, row["content"],
                 json.dumps(embedding), row["tags"], datetime.now(timezone.utc).isoformat())
            )
            imported += 1
        except sqlite3.IntegrityError:
            pass
    target_conn.commit()
    return imported


def merge_dedup(records, target_conn, embed_model: str, re_embed: bool, scope: str, agent_id: str, team_id: str, threshold: float):
    # Load existing embeddings for comparison
    existing = target_conn.execute("SELECT embedding FROM memories").fetchall()
    existing_embeddings = [json.loads(r["embedding"]) for r in existing]

    imported = skipped = 0
    for row in records:
        embedding = get_embedding(row["content"], embed_model) if re_embed else json.loads(row["embedding"])

        # Check similarity against all existing records
        is_duplicate = any(
            cosine_similarity(embedding, ex_emb) >= threshold
            for ex_emb in existing_embeddings
        )

        if is_duplicate:
            skipped += 1
            continue

        new_id = secrets.token_hex(8)
        target_conn.execute(
            """INSERT INTO memories (id, agent_id, team_id, scope, content, embedding, tags, created_at, conflict_ids, resolved)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', 0)""",
            (new_id, agent_id, team_id, scope, row["content"],
             json.dumps(embedding), row["tags"], datetime.now(timezone.utc).isoformat())
        )
        existing_embeddings.append(embedding)
        imported += 1

    target_conn.commit()
    return imported, skipped


def merge_federated(dataset_path: Path, db_path: Path):
    """Register the dataset as a federated source — no data moves."""
    federated_config = db_path.parent / "federated.json"
    config = json.loads(federated_config.read_text()) if federated_config.exists() else {"sources": []}

    source_path = str(dataset_path / "knowledge.db")
    if source_path not in config["sources"]:
        config["sources"].append(source_path)

    federated_config.write_text(json.dumps(config, indent=2) + "\n")
    return len(config["sources"])


def main():
    parser = argparse.ArgumentParser(description="Import an AgentCommons dataset into your memory database.")
    parser.add_argument("--dataset",         required=True,  help="Path or agentcommons-relative path to dataset")
    parser.add_argument("--db",              required=True,  help="Path to your memory.db")
    parser.add_argument("--merge",           default="union", choices=["union", "dedup", "federated"], help="Merge strategy (default: union)")
    parser.add_argument("--scope",           default="team", choices=["agent", "team"], help="Scope for imported memories (default: team)")
    parser.add_argument("--agent-id",        default="agentcommons-import", help="Agent ID to attribute imported memories to")
    parser.add_argument("--team-id",         required=True,  help="Your team ID")
    parser.add_argument("--dedup-threshold", type=float, default=0.92, help="Similarity threshold for dedup merge (default: 0.92)")
    parser.add_argument("--re-embed",        action="store_true", help="Re-embed records using your local model before importing")
    parser.add_argument("--embed-model",     default="nomic-embed-text", help="Embedding model to use for re-embedding (default: nomic-embed-text)")
    args = parser.parse_args()

    dataset_path = resolve_dataset_path(args.dataset)
    db_path = Path(args.db)

    if not db_path.exists():
        print(f"Error: database not found at {db_path}")
        return

    records, metadata = load_dataset(dataset_path)
    print(f"Dataset:        {dataset_path.name}")
    print(f"Records:        {len(records)}")
    print(f"Embed model:    {metadata.get('embedding_model', 'unknown')}")
    print(f"Merge strategy: {args.merge}")
    print()

    if args.merge == "federated":
        count = merge_federated(dataset_path, db_path)
        print(f"Federated source registered. Total federated sources: {count}")
        print(f"The MCP server will query this database at retrieval time — no data was moved.")
        return

    target_conn = get_target_conn(db_path)

    if args.merge == "union":
        imported = merge_union(records, target_conn, args.embed_model, args.re_embed, args.scope, args.agent_id, args.team_id)
        print(f"Union merge complete. Imported: {imported} records.")

    elif args.merge == "dedup":
        imported, skipped = merge_dedup(records, target_conn, args.embed_model, args.re_embed, args.scope, args.agent_id, args.team_id, args.dedup_threshold)
        print(f"Dedup merge complete. Imported: {imported} records. Skipped (duplicates): {skipped}.")

    target_conn.close()


if __name__ == "__main__":
    main()
