---
type: concept
tags: [llm-wiki, maintenance]
updated: 2026-08-24
---

# Wiki maintenance workflow

Operating schema for [[index]]. Agents should also use
`math/.cursor/skills/math-wiki/SKILL.md`.

Keep this wiki sparse. Add claims only when the user asks to add them, asks to
ingest a source, or says to file an answer back.

`math/docs/` is the vendor wiki. This folder is the LLM layer.

## Contract

- `math/docs/` — immutable vendor source.
- `wiki/sources/` — summaries with provenance.
- `wiki/codebase/` — architecture.
- `wiki/domain/` — publish / RTP / RGS facts.
- `wiki/concepts/` — conventions.
- `wiki/analyses/` — filed answers.
- [[index]] and [[log]] on every meaningful change.

## Ingest

Read the source → summarize in `wiki/sources/` → update affected pages →
update [[index]] → append [[log]].

## Query

Read [[index]] first. Cite `[[wikilinks]]`. If the answer is reusable, file
under `wiki/analyses/`.

## Lint

Report orphans, missing wikilinks, stale claims, contradictions, and drift vs
`math/docs/`. Do not silently resolve contradictions.
