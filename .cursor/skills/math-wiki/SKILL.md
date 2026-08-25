---
name: math-wiki
description: >-
  Use when creating, updating, querying, linting, or maintaining the Math SDK
  wiki under math/wiki/: Obsidian vault, source summaries, codebase pages,
  domain pages, analyses, index.md, or log.md. Official Stake Engine Math SDK
  docs live in math/docs/ (vendor wiki). Complements math-sdk for engine work.
---

# Math SDK Wiki

Maintain `math/wiki/` as a persistent LLM knowledge layer for the Stake Engine
Math SDK in this repo. It is durable project memory — not a scratchpad and not
a copy of the vendor docs.

Keep it sparse. Add pages only when the user asks to add them, asks to ingest
a source, or explicitly says to file an answer back into the wiki.

**Vendor wiki (read-only):** `math/docs/` — Stake Engine MkDocs. Never rewrite
those pages to "fix" them. Summarize into `math/wiki/sources/` and cite paths.

**Engine work:** skill `math-sdk` (`math/.cursor/skills/math-sdk/SKILL.md`).

## First steps

Before changing or answering from the wiki:

1. Read `math/wiki/index.md`.
2. Skim latest log entries (`grep "^## \[" math/wiki/log.md | tail -10`).
3. Follow links to codebase, domain, source, or analysis pages.
4. Follow `math/AGENTS.md`.

If `math/wiki/index.md` or `math/wiki/log.md` is missing, bootstrap with
`math/wiki/index.md`, `math/wiki/log.md`, `math/wiki/sources/`,
`math/wiki/codebase/`, `math/wiki/domain/`, `math/wiki/concepts/`,
`math/wiki/analyses/`.

## Directory contract

| Path | Purpose | Rule |
| --- | --- | --- |
| `math/docs/` | Official Stake Engine wiki | Read only. Cite as source. |
| `math/src/`, `math/games/` | Engine + games | Code of record; wiki describes it |
| `math/wiki/sources/` | Source summaries with provenance | Cite `math/docs/...` path or URL |
| `math/wiki/codebase/` | SDK layout, game architecture | Prefer update over duplicate |
| `math/wiki/domain/` | RTP, books, RGS publish rules | Non-file-specific facts |
| `math/wiki/concepts/` | Wiki / engine conventions | Workflows, patterns |
| `math/wiki/analyses/` | Saved answers and audits | File useful synthesis |
| `math/wiki/index.md` | Content catalog | Update on every meaningful change |
| `math/wiki/log.md` | Chronological audit trail | Append parseable entries |

## Page rules

- Use kebab-case filenames.
- Start every page with YAML frontmatter containing at least `type`, `tags`,
  and `updated`.
- Use Obsidian wikilinks like `[[codebase/gladiator-tower]]`.
- Prefer updating existing pages over creating near-duplicates.
- Cite vendor docs inline: `(from [[sources/stake-engine-math-sdk]])` or
  `(from math/docs/rgs_docs/data_format.md)`.
- Mark uncertainty with `?` or a blockquote warning.
- Flag contradictions: `> ⚠️ Contradicts [[other-page]]: ...` — surface them,
  do not silently resolve.
- Do not paste full vendor chapters into the wiki. Link + 3–6 durable facts.

## Operations

### Ingest

When a user adds a source (file, URL, or `math/docs/` page) or asks to process
material:

1. Read the source in full.
2. Briefly discuss key takeaways (2–4 bullets). Ask what to emphasize before
   writing, unless the user already said to file it.
3. Create or update a summary in `math/wiki/sources/` with provenance.
4. Update affected codebase / domain / concept pages.
5. Add a new page only when the idea has no home and will accumulate later.
6. Update `math/wiki/index.md`.
7. Append to `math/wiki/log.md`:

```markdown
## [YYYY-MM-DD] ingest | Title

- summary: wiki/sources/source-slug.md
- touched: wiki/codebase/example.md, wiki/domain/example.md
- new: wiki/codebase/new-page.md
- notes: contradictions, uncertainty, or open questions
```

8. Report back: pages changed, pages created, contradictions surfaced.

### Query

Read the index first, then linked pages. Answer with `[[wikilinks]]`. Cite
`math/docs/` when quoting vendor rules. Ask: _"File this back into the wiki?"_
— if yes, save under `math/wiki/analyses/` with `type: analysis`, update the
index, append a `query` entry to the log.

### Lint

When asked to lint or audit, report:

- **Orphans** — pages with no inbound `[[links]]`
- **Missing pages** — `[[brackets]]` with no file
- **Contradictions** — opposing claims
- **Stale claims** — wiki older than a newer source on the same topic
- **Coverage gaps** — concepts used in `math/games/` but missing from the wiki
- **Vendor drift** — wiki claims that disagree with `math/docs/`

Do not silently resolve contradictions.

## Current repo context

This wiki sits beside a vendored Stake Engine Math SDK. Live product games
are **Gladiator Tower** (`math/games/gladiator-tower/`, session climb) and
**Luma Keno** (`math/games/luma-keno/`, hit-count books). Sample slot games
may still exist under `math/games/0_0_*`.

Math generation must follow [[domain/stake-rating-limits]] (default 3-Star)
and [[concepts/tower-math-from-ratings]]. Do not create a wiki page for every
`src/` module. Prefer [[codebase/sdk-layout]] + vendor
`math/docs/math_docs/directory.md`.
