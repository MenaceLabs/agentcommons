# Merge Approaches

When you import a community dataset into your MCP Memory Server, you have four options for how it combines with your existing knowledge.

---

## 1. Simple Union Merge

**Complexity:** Low
**Best for:** Same embedding model, duplicates acceptable, speed matters

Appends all records from the imported dataset directly into your database. No deduplication. Fastest option.

```bash
python tools/import.py --dataset community/cloudflare/cloudflare-workers-patterns \
  --db ./memory.db \
  --merge union
```

**When to use:** You're pulling a dataset for the first time and just want the knowledge available quickly.

---

## 2. Deduplication + Merge

**Complexity:** Moderate
**Best for:** Quality-conscious merges, avoiding redundant memories

Runs a cosine similarity pass before inserting each record. Records with similarity above a configurable threshold against existing memories are skipped or flagged rather than duplicated.

```bash
python tools/import.py --dataset community/cloudflare/cloudflare-workers-patterns \
  --db ./memory.db \
  --merge dedup \
  --dedup-threshold 0.92
```

**When to use:** Your database already has knowledge in this domain and you want to add without creating noise.

---

## 3. Federated Query

**Complexity:** Low
**Best for:** Early-stage sharing, no trust established yet, no data movement

No merge happens. Both databases are queried at retrieval time and results are combined and ranked. The imported dataset stays in a separate file — your data never mixes with theirs.

```bash
python tools/import.py --dataset community/cloudflare/cloudflare-workers-patterns \
  --db ./memory.db \
  --merge federated
```

This creates a `federated.json` config file that the MCP server reads at startup, querying all registered databases simultaneously.

**When to use:** You want to try a dataset before committing to a merge, or you don't fully trust the source yet.

---

## 4. Distillation Merge

**Complexity:** High
**Best for:** Maximum knowledge synthesis, canonical releases

Groups semantically similar records into clusters using cosine similarity, then runs an LLM pass over each cluster to synthesize a single high-quality canonical record. The result is a smaller, denser, higher-quality dataset.

```bash
python tools/distill.py \
  --datasets community/cloudflare/cloudflare-workers-patterns community/cloudflare/cloudflare-dns-patterns \
  --out distillations/cloudflare-v1.0.0 \
  --model nomic-embed-text
```

**When to use:** You are an AgentCommons maintainer producing an official distillation release, or you are synthesizing multiple datasets for your own high-quality internal knowledge base.

---

## Recommended Path

```
Start here         →    Grow into this    →    Graduate to this
Federated Query         Dedup + Merge          Distillation
(no commitment)         (quality merge)        (maximum synthesis)
```

---

## Embedding Model Compatibility

All merge approaches require compatible embedding models to produce meaningful similarity scores.

- **Same model:** merge directly, all approaches available
- **Different model:** use `--re-embed` flag to re-embed the imported dataset with your model before merging (adds compute time, solves alignment)

```bash
python tools/import.py --dataset community/kubernetes/k8s-patterns \
  --db ./memory.db \
  --merge dedup \
  --re-embed \
  --embed-model nomic-embed-text
```
