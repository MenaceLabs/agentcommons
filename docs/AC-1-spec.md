# AC-1: AgentCommons Dataset Specification

**Version:** 1.0.0
**Status:** Draft
**Date:** 2026-03-30

---

## 1. Purpose

This specification defines the standard format for AgentCommons datasets — portable collections of domain knowledge that any AI agent can produce, share, and consume regardless of what memory system or MCP server created them.

AC-1 is a minimum viable specification. It defines what a valid dataset looks like. It does not prescribe how datasets are produced internally — only what they must look like when submitted.

---

## 2. Terminology

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT", and "MAY" in this document are to be interpreted as described in [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).

---

## 3. Dataset Structure

A dataset MUST be a directory containing exactly three files:

```
dataset-name/
├── knowledge.db       # SQLite database containing memories
├── metadata.json      # Dataset metadata
└── README.md          # Human-readable description
```

- The directory name MUST match the `name` field in `metadata.json`.
- The directory name MUST be lowercase, using only alphanumeric characters and hyphens.
- The total dataset size MUST NOT exceed 50 MB.

---

## 4. Database Format

### 4.1 Container

The database file MUST be a valid SQLite 3 database named `knowledge.db`.

SQLite is the interchange format. Tools MAY use any internal runtime format — the spec only governs the submitted artifact.

### 4.2 Schema

The database MUST contain a table named `memories` with the following schema:

```sql
CREATE TABLE memories (
    id        TEXT PRIMARY KEY,
    content   TEXT NOT NULL,
    embedding TEXT NOT NULL,
    tags      TEXT NOT NULL DEFAULT '[]',
    source_at TEXT NOT NULL
);
```

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | Unique identifier. Any format accepted. |
| `content` | TEXT | NOT NULL | The memory content. |
| `embedding` | TEXT | NOT NULL | JSON-encoded vector (array of floats). |
| `tags` | TEXT | NOT NULL, DEFAULT '[]' | JSON-encoded array of tag strings. |
| `source_at` | TEXT | NOT NULL | ISO 8601 timestamp (e.g., `2026-03-24T14:30:00`). |

The database MUST NOT contain additional tables.

The database MUST NOT contain columns beyond those specified above. Tool-specific or identity-related fields (agent IDs, team IDs, scope, etc.) MUST be stripped before submission.

### 4.3 Encoding

All text content MUST be UTF-8 encoded.

---

## 5. Content Requirements

### 5.1 Scope

Datasets MUST contain only domain knowledge — general-purpose information about technologies, patterns, configurations, or processes that is useful to agents beyond the original context.

Datasets MUST NOT contain:
- Personal or operational context (session state, project-specific plans, internal identifiers)
- Credentials, API keys, tokens, or secrets
- Personally identifiable information (PII)
- Copyrighted material reproduced in full

### 5.2 Length

Each memory's `content` field:
- MUST be at least 20 characters
- MUST NOT exceed 10,000 characters
- MUST NOT be empty or whitespace-only

### 5.3 PII

Content MUST NOT contain patterns matching:
- Email addresses
- Phone numbers
- Social Security Numbers (or equivalent national identifiers)
- Credential strings (`password=`, `secret=`, `api_key=`, `token=`, etc.)
- IP addresses

The validation tooling scans for these patterns. Contributors are responsible for reviewing flagged content before submission.

---

## 6. Tagging

### 6.1 Rules

- Each memory MUST have at least 1 tag and at most 5 tags.
- Tags MUST be lowercase.
- Tags MUST contain only alphanumeric characters and hyphens (`a-z`, `0-9`, `-`).
- Tags MUST NOT exceed 32 characters each.
- Tags MUST be stored as a JSON-encoded array in the `tags` column.

### 6.2 Recommended Convention

Tags SHOULD follow a two-tag pattern: one identifying the **technology or domain** (e.g., `cloudflare`, `postgresql`, `kubernetes`) and one identifying the **knowledge type** (e.g., `configuration`, `security`, `deployment`, `troubleshooting`).

### 6.3 Blocked Tags

The following tags MUST NOT appear in any submitted dataset:

`personality`, `relationship`, `style`, `personal`, `private`, `preferences`, `feedback`, `decision`

These tags indicate personal or interpersonal context and are not appropriate for community knowledge sharing.

---

## 7. Embeddings

### 7.1 Declaration

The embedding model used MUST be declared in `metadata.json` via the `embedding_model` field.

### 7.2 Format

Embeddings MUST be stored as JSON-encoded arrays of floating-point numbers in the `embedding` column (e.g., `[0.123, -0.456, ...]`).

All embeddings within a dataset MUST have the same dimensionality.

### 7.3 Recommended Model

The recommended embedding model is **`nomic-embed-text`** (768 dimensions). Datasets using this model are compatible out of the box with the AgentCommons tooling and MCP Memory Server.

Datasets using other embedding models are accepted. Consumers requiring vector compatibility are responsible for re-embedding at import time.

---

## 8. Metadata

### 8.1 Format

`metadata.json` MUST be valid JSON and MUST contain the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Dataset name. Must match directory name. |
| `version` | string | Semantic version (e.g., `1.0.0`). |
| `embedding_model` | string | Name of the embedding model used. |
| `topic_tags` | array[string] | Tags for dataset discovery and categorization. |
| `agent_type` | string | Type of agent that produced the data (e.g., `engineering`, `research`, `support`). |
| `record_count` | integer | Number of records in `knowledge.db`. MUST match actual count. |
| `language` | string | ISO 639-1 language code (e.g., `en`). |
| `submitted_by` | string | Contributor identity (e.g., GitHub username). |
| `submitted_at` | string | Submission date in ISO 8601 format (`YYYY-MM-DD`). |
| `provenance` | array[string] | Lineage information — source agent, team, methodology. |
| `description` | string | Human-readable summary of the dataset contents. |

All fields are required. No field MAY contain placeholder or template values (e.g., `"your-github-username"`, `"YYYY-MM-DD"`).

### 8.2 Spec Version

`metadata.json` SHOULD include a `spec_version` field with the value `"AC-1.0"`. This field will become MUST in future spec revisions.

### 8.3 Extension

`metadata.json` MAY include additional fields beyond those listed above. Tooling MUST ignore unrecognized fields. This allows tools to include custom metadata without breaking compatibility.

---

## 9. README

Each dataset MUST include a `README.md` that describes:
- What domain knowledge the dataset contains
- How it was generated (agent type, tasks performed, time period)
- Known gaps or limitations

The README MUST NOT consist solely of unfilled template text.

---

## 10. Validation

Datasets MUST pass the AgentCommons validation checks before submission:

1. All three required files are present (`knowledge.db`, `metadata.json`, `README.md`)
2. All required metadata fields are present and non-template
3. `record_count` matches the actual number of rows in `knowledge.db`
4. No blocked tags are present in any memory record
5. PII pattern scan produces no unreviewed matches
6. README contains substantive content

The reference validation tool is `tools/validate.py` in the AgentCommons repository.

---

## 11. Submission Path

Datasets conforming to this spec are submitted via pull request to the AgentCommons repository under `community/<domain>/<dataset-name>/`.

GitHub Actions will run automated validation on all submissions. PRs that fail validation will not be merged.

---

## 12. Versioning

This specification is versioned as `AC-<major>.<minor>`.

- **Minor** revisions add SHOULD/MAY guidance or clarifications. Existing datasets remain valid.
- **Major** revisions may change MUST requirements. A migration guide will accompany any major revision.

Current version: **AC-1.0**

---

## 13. What This Spec Does Not Cover

The following are explicitly out of scope for AC-1 and may be addressed in future revisions based on community experience:

- Relationships between memories within a dataset
- Confidence or quality scores per record
- Structured content types beyond plain text
- Dataset update/supersede mechanisms
- Cross-dataset deduplication standards
- Discovery and search interfaces
- Distillation methodology (see `docs/distillation-standard.md`)

---

## 14. Quick Reference

**To produce a valid AC-1 dataset, you need:**

1. A SQLite database with the `memories` table (5 columns, no extras)
2. Embeddings as JSON float arrays, all same dimensionality
3. 1-5 lowercase hyphenated tags per memory, no blocked tags
4. Content between 20-10,000 characters, no PII
5. A `metadata.json` with all 11 required fields filled in
6. A `README.md` that describes the dataset
7. Everything in a directory named to match your dataset name
8. Total size under 50 MB

That's it. Ship it.
