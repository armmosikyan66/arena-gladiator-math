# AGENTS.md — Stake Engine Math SDK

Guidance for agents working in `math/`. Companion to the web app in `web/`.

## Project at a glance

- **What**: Stake Engine Math SDK (Python ≥ 3.12). Precomputes round books and
  lookup tables for the RGS. Optional Rust optimizer.
- **Docs**: Official wiki `math/docs/` (MkDocs). Hosted:
  https://stakeengine.github.io/math-sdk/
- **LLM wiki**: `math/wiki/` — you maintain it (skill `math-wiki`).
- **Engine skill**: `math/.cursor/skills/math-sdk/SKILL.md` (also mirrored at
  repo `.cursor/skills/math-sdk/`).
- **Keno skill**: `.cursor/skills/keno-math/` — hit-count books, exact
  hypergeometric weights, frontend draw reconstruction (not a slot).
- **Live games**: `math/games/gladiator-tower/` (session climb) and
  `math/games/luma-keno/` (hit-count keno).

## Coding conventions

- Game-specific logic in `games/<id>/`. Shared reusable logic in `src/`.
- Copy `games/template/` (or the closest sample) for a new game.
- Seed RNG with `reset_seed(sim)`. Calculate → WinManager → emit event.
- `payoutMultiplier = int(round(mult * 100))`, 0.1× steps (multiple of 10).
- LUT payout column must match the book. Publish only `library/publish_files/`.
- **Rating limits:** default 3-Star. Build Tower math from
  `.cursor/skills/math-sdk/rating-limits.md` (probabilities → RTP budget →
  survival P_k → validation). Fail the build on gate violations; do not clamp.
  Wiki: `math/wiki/domain/stake-rating-limits.md`.

## Wiki — you maintain it

`math/docs/` is the vendor wiki. **Never modify it** to "correct" Stake docs.
`math/wiki/` is the LLM layer: project facts, Tower architecture, publish
gotchas, filed analyses.

### Before wiki work

1. Read `math/wiki/index.md`.
2. Skim the last ~10 entries of `math/wiki/log.md`.
3. Only then act.

Keep the wiki sparse. Add pages only when the user asks to add them, asks to
ingest a source, or says to file an answer back.

### Categories

- `wiki/sources/<slug>.md` — one summary per ingested doc (usually a
  `math/docs/` page or external spec).
- `wiki/codebase/<slug>.md` — SDK layout, game architecture.
- `wiki/domain/<slug>.md` — books, RTP, RGS publish rules, **rating limits**.
- `wiki/concepts/<slug>.md` — workflows and conventions.
- `wiki/analyses/<slug>.md` — filed Q&A.

### Page conventions

- Filenames: `kebab-case.md`.
- Frontmatter: `type`, `tags`, `updated`.
- Cross-link with `[[wikilinks]]`.
- Cite vendor paths: `(from math/docs/rgs_docs/data_format.md)`.
- Flag uncertainty. Surface contradictions; do not silently resolve.

### Log format

```markdown
## [YYYY-MM-DD] ingest | Title

- summary: wiki/sources/source-slug.md
- touched: wiki/codebase/example.md
- new: wiki/domain/example.md
- notes: …
```

Operations: ingest, query, lint — see `.cursor/skills/math-wiki/SKILL.md`.
