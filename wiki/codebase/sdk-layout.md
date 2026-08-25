---
type: codebase
tags: [math-sdk, layout]
updated: 2026-08-24
---

# SDK layout

Paths from repo root. Vendor catalog: `math/docs/math_docs/directory.md`
(from [[sources/stake-engine-math-sdk]]).

| Path | Edit? | Role |
| --- | --- | --- |
| `math/src/` | Rarely | Shared calculations, events, state, wins, writers |
| `math/games/template/` | Copy | New-game skeleton |
| `math/games/gladiator-tower/` | Yes | Live product math |
| `math/games/0_0_*` | Samples | Slot examples (lines/ways/cluster/scatter) if present |
| `math/optimization_program/` | Rarely | Rust LUT weight optimizer |
| `math/utils/` | Helpers | Analytics, LUT merge, zstd, hashes |
| `math/tests/` | Yes | Win-calculation pytest |
| `math/docs/` | Never | Vendor MkDocs wiki |
| `math/wiki/` | Agents | This layer |

Generated (typically gitignored): `math/games/<id>/library/` — books, LUTs,
configs, `publish_files/`.

Commands from `math/`: `make setup`, `make run GAME=<id>`, `make test`.

## Related

- [[codebase/gladiator-tower]]
- [[domain/stake-engine-publish]]
