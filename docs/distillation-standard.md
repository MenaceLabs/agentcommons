# Distillation Standard

How AgentCommons produces official distillation releases and what makes them trustworthy.

---

## What Is a Distillation Release?

A distillation release is a curated, synthesized dataset produced by AgentCommons from community contributions. It is:

- **Deduplicated** — semantically redundant records are collapsed
- **Synthesized** — LLM pass over semantic clusters produces single high-quality canonical records
- **Versioned** — every release has a semantic version and a full provenance record
- **Open** — freely downloadable, forkable, buildable-upon

Distillation releases are published under `/distillations/` and clearly distinguished from raw community submissions.

---

## Provenance Record

Every distillation release includes a `provenance.json` alongside its `metadata.json`:

```json
{
  "release": "distillations/cloudflare-v1.0.0",
  "produced_at": "2026-03-24",
  "produced_by": "AgentCommons",
  "methodology": "dedup-then-distill",
  "embedding_model": "nomic-embed-text",
  "source_datasets": [
    "community/cloudflare/cloudflare-workers-patterns@1.0.0",
    "community/cloudflare/cloudflare-dns-patterns@1.2.0",
    "community/cloudflare/cloudflare-r2-storage@1.0.0"
  ],
  "input_record_count": 487,
  "output_record_count": 203,
  "dedup_threshold": 0.92,
  "notes": "First official Cloudflare domain distillation. Workers patterns dominate. DNS coverage is thinner — more community contributions welcome."
}
```

---

## Release Cadence

Distillation releases are not automated. They are produced when:

- Sufficient community contributions exist in a topic area to make synthesis worthwhile
- A maintainer has reviewed source datasets for PII and quality
- The output has been spot-checked for accuracy

There is no fixed schedule. Quality over cadence.

---

## Forking and Building On Top

Anyone can take an official distillation release and:

- Merge it with their own domain knowledge
- Run their own distillation pass to produce a higher-quality result
- Submit that result back to AgentCommons as a community dataset

If you build on top of an official release, list it in your dataset's `provenance` field. Lineage is always traceable.

AgentCommons does not own the knowledge — it manages the canonical release. The community owns the commons.

---

## Distillation Methodology (v1)

1. **Collect** source datasets (same embedding model required)
2. **Union merge** all records into a working database
3. **Cluster** using cosine similarity — records above `0.85` threshold grouped together
4. **Synthesize** each cluster: LLM pass produces a single canonical record that captures the best of the group
5. **Review** output manually — spot-check for accuracy, hallucination, PII
6. **Publish** with full provenance record

This methodology will evolve. Each release documents which version of the methodology was used.
