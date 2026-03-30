# AgentCommons

A federated knowledge sharing platform for AI agent memory datasets.

Agents accumulate domain knowledge through real work. AgentCommons lets that knowledge escape the silo — shared, merged, and distilled into something better than any individual contributor could build alone.

**Think Docker Hub, but for agent memory.**

---

## How It Works

1. An agent accumulates domain knowledge through real tasks using the [MCP Memory Server](https://github.com/MenaceLabs/mcp_memory_server)
2. The agent exports domain-scoped memories as a dataset (identity stripped, domain only)
3. The dataset is submitted here — tagged with embedding model, topic, version
4. The community discovers and imports datasets compatible with their stack
5. AgentCommons runs periodic distillation passes — synthesizing community contributions into curated canonical releases

---

## Repository Structure

```
agentcommons/
├── community/          # Community-submitted datasets, organized by topic
│   ├── cloudflare/
│   ├── kubernetes/
│   ├── healthcare/
│   └── .../
├── distillations/      # Official AgentCommons distillation releases (curated, versioned)
│   └── v1.0.0/
├── submissions/        # Submission staging area and templates
│   └── .template/      # Copy this to submit a dataset
├── tools/              # Export, import, merge, and validation CLI tools
└── docs/               # Standards, submission guide, merge documentation
```

---

## Dataset Standard

All datasets must conform to the **[AC-1 Dataset Specification](docs/AC-1-spec.md)** — the formal standard governing schema, metadata, tagging, embeddings, content, and privacy requirements. AC-1 uses RFC 2119 compliance levels (MUST/SHOULD/MAY) and is the authoritative reference for contributors using any memory tool.

### Format Overview

Every dataset is a folder containing three files:

```
my-dataset/
├── knowledge.db       # SQLite — domain memories only, identity stripped
├── metadata.json      # Required metadata (see below)
└── README.md          # Human-readable description of the dataset
```

**Required metadata fields (`metadata.json`):**
```json
{
  "name": "cloudflare-workers-patterns",
  "version": "1.0.0",
  "embedding_model": "nomic-embed-text",
  "topic_tags": ["cloudflare", "workers", "edge-computing"],
  "agent_type": "engineering",
  "record_count": 142,
  "language": "en",
  "submitted_by": "community",
  "submitted_at": "2026-03-24",
  "provenance": [],
  "description": "Domain knowledge about Cloudflare Workers patterns, gotchas, and performance optimizations accumulated through real engineering tasks."
}
```

**Default embedding model:** `nomic-embed-text` — datasets using this model are natively compatible with the MCP Memory Server and require no re-embedding on import.

Other models are fully supported — declare them in `embedding_model` and users can filter by compatibility.

---

## Submitting a Dataset

1. Export your domain memories using the tools in `/tools/export.py`
2. Copy `/submissions/.template/` and fill in your dataset
3. Open a Pull Request to `community/<your-topic>/`
4. A maintainer will review for PII, metadata completeness, and scope

See [docs/submission-guide.md](docs/submission-guide.md) for full instructions and [docs/AC-1-spec.md](docs/AC-1-spec.md) for the formal dataset standard.

---

## Validation

Every dataset is validated against the AC-1 spec before it can be merged. Run it locally before submitting:

```bash
python tools/validate.py --dataset ./my-dataset
```

The validator checks:

| Check | What it does |
|-------|-------------|
| File structure | `knowledge.db`, `metadata.json`, and `README.md` all present |
| Dataset size | Total size under 50 MB |
| Directory name | Lowercase alphanumeric + hyphens, matches metadata `name` |
| Schema | `memories` table has exactly 5 required columns, no extra tables |
| Metadata | All 11 required fields present, no unfilled template values |
| Spec version | `spec_version` declared in metadata (warning if missing) |
| Record count | `record_count` in metadata matches actual database rows |
| Content length | Each memory between 20–10,000 characters, no empty content |
| Tag format | 1–5 tags per memory, lowercase alphanumeric + hyphens, max 32 chars each |
| Blocked tags | None of the 8 blocked personal tags present |
| Embedding consistency | All embeddings have the same dimensionality |
| PII scan | Regex scan for emails, phone numbers, SSNs, credentials, IP addresses |
| README | Contains substantive content, not just template text |

Pull requests to `community/` trigger this automatically via GitHub Actions. PRs that fail validation will not be merged.

---

## Official Distillation Releases

AgentCommons periodically runs distillation passes over community contributions — deduplicating, synthesizing, and quality-vetting into canonical releases published under `/distillations/`.

Distillation releases carry full provenance records (which source datasets were merged, embedding model, methodology, date). They are open — anyone can fork them, run their own distillation, and publish something better. The lineage is always traceable.

---

## Importing a Dataset

```bash
python tools/import.py --dataset community/cloudflare/cloudflare-workers-patterns --db /path/to/your/memory.db
```

Datasets using the same embedding model as your server are imported directly. Datasets using a different model can be re-embedded on import with `--re-embed`.

---

## Embedding Model Compatibility

| Model | Native Support | Notes |
|-------|---------------|-------|
| `nomic-embed-text` | Yes — default | Recommended. Works out of the box with MCP Memory Server |
| Other models | Declared | Fully supported — filter by model on import, or re-embed |

---

## Privacy Rules

- **Only domain-scoped memories are shareable.** Personal, interpersonal, and operational memories are never eligible for submission.
- Memories with blocked tags (`personality`, `relationship`, `style`, `personal`, `private`, `preferences`, `feedback`, `decision`) are excluded from export automatically.
- Submitters are responsible for ensuring no PII is included. See the [AC-1 spec](docs/AC-1-spec.md) for full privacy and content requirements.

---

## Deployment Models

| Model | Description |
|-------|-------------|
| Community Hub | This repository — open source, community-governed |
| Black Box Deployment | Self-hosted, air-gapped private instance for enterprise/government |
| Hosted Private Hub | Managed private hub for organizations that don't want to self-host |

---

Built on [MCP Memory Server](https://github.com/MenaceLabs/mcp_memory_server) by [MenaceLabs](https://github.com/MenaceLabs).
