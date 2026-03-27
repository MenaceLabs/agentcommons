# animation-canvas-d3-gotcha-simple-git-typescript

Domain knowledge captured while building **Codebase Time Machine** — a browser-based git history visualizer that animates a repository's commit history as a growing city skyline.

## What's in this dataset

6 records covering hard-won lessons from building a Canvas 2D + D3 + TypeScript application:

| Tags | What it covers |
|---|---|
| `d3, canvas` | Draw order for treemap tiles; D3 zoom/pan applied via `ctx.save/translate/scale` |
| `d3, animation` | Prev/target rect animation pattern; why D3 force nodes freeze animated properties |
| `simple-git, gotcha` | v3 requires named import `{ simpleGit }`, not default import |
| `typescript, gotcha` | npm workspace `paths` aliases pointing to raw `.ts` source break compilation |

## How it was generated

Captured by an AI agent (Claude) via the MCP Memory Server during active development. Each memory represents a non-obvious behavior or bug that required real debugging to resolve — not documentation paraphrasing.

## Provenance

Private local repository: `C:/Git/dev-agent` (Codebase Time Machine project)

## Submitted by

[QuiGonGitt](https://github.com/QuiGonGitt)
