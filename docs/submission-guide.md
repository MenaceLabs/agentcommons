# Submission Guide

How to export your agent's domain knowledge and contribute it to AgentCommons.

All datasets must conform to the **[AC-1 Dataset Specification](AC-1-spec.md)**. This guide walks through the practical steps — the spec is the formal reference for requirements.

---

## Before You Submit

Your dataset must contain **domain knowledge only**. This means:

- Technical patterns, gotchas, solutions, configurations
- Framework behavior, API quirks, performance observations
- Process knowledge, best practices, lessons learned from real tasks

**Never include:**
- Personal or interpersonal memories
- Credentials, tokens, API keys, or any secrets
- Anything with blocked tags (`personality`, `relationship`, `style`, `personal`, `private`, `preferences`, `feedback`, `decision`)
- Operational details about your organization, clients, or internal systems

The export tool enforces this automatically — but you are responsible for a final review before submitting.

---

## Step 1 — Export Your Dataset

Run the export tool from your project directory (where your `memory.db` lives):

```bash
python /path/to/agentcommons/tools/export.py \
  --db ./memory.db \
  --tags cloudflare,workers,edge-computing \
  --out ./my-dataset
```

This will:
- Extract memories matching the specified tags
- Strip all agent and team identity fields
- Generate a `metadata.json` with your embedding model and record count
- Create a `README.md` template for you to fill in

---

## Step 2 — Fill In the Metadata

Open `my-dataset/metadata.json` and complete all fields:

```json
{
  "name": "your-dataset-name",
  "version": "1.0.0",
  "embedding_model": "nomic-embed-text",
  "topic_tags": ["your", "topic", "tags"],
  "agent_type": "engineering",
  "record_count": 0,
  "language": "en",
  "submitted_by": "your-github-username",
  "submitted_at": "YYYY-MM-DD",
  "provenance": [],
  "description": "What does this dataset contain and where did the knowledge come from?"
}
```

**`provenance`** — if your dataset was built on top of other AgentCommons datasets, list them here:
```json
"provenance": ["community/cloudflare/cloudflare-workers-v1.0.0"]
```

---

## Step 3 — Write Your README

Your `README.md` should answer:
- What domain does this cover?
- What kind of agent generated it (engineering, research, support, etc.)?
- What embedding model was used?
- Any known gaps or limitations?
- Any special usage notes?

---

## Step 4 — Validate

Run the validator before submitting:

```bash
python /path/to/agentcommons/tools/validate.py --dataset ./my-dataset
```

This checks AC-1 compliance:

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

## Step 5 — Submit via Pull Request

1. Fork the AgentCommons repository
2. Copy your dataset folder to `community/<primary-topic>/<dataset-name>/`
3. Open a Pull Request with the title: `[submission] <dataset-name> v<version>`
4. A maintainer will review for metadata completeness, scope, and PII

---

## Versioning

Use semantic versioning: `MAJOR.MINOR.PATCH`

- `PATCH` — added records, minor corrections
- `MINOR` — significant new coverage of the same topic
- `MAJOR` — breaking change (different embedding model, major scope change)

When updating an existing dataset, submit to the same path with an incremented version in `metadata.json`. Old versions are preserved in git history.

---

## Using a Different Memory Tool (BYOMCP)

You don't need to use the MCP Memory Server to contribute. Any tool that produces a dataset conforming to the [AC-1 spec](AC-1-spec.md) is welcome. The key requirements:

- SQLite database with the correct `memories` table schema
- Embedding model declared in metadata
- Tags follow AC-1 formatting rules (1-3 tags, lowercase, alphanumeric + hyphens)
- No blocked tags, no PII, domain knowledge only

See the spec for the full list of requirements.

---

## Invite-Only (v1)

AgentCommons is currently invite-only while submission standards and trust mechanisms mature. If you'd like to contribute, open an issue with the label `invite-request`.
