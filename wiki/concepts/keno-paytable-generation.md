---
type: concept
tags: [keno, paytable, rtp, geometric, lattice, luma-keno]
updated: 2026-09-02
---

# Keno paytable generation — multipliers, payout, RTP

How luma-keno **builds** an Off multiplier row. Code of record:
`math/games/luma-keno/easy_off_classic.py` (classic geometric),
`easy_off_medium.py` (medium geometric), `easy_off_high.py` (high geometric),
`easy_off_low.py` (low leftover-share), `keno_pick_one.py` (pick_1 lattice).
Shipped numbers: [[domain/keno-xtreme-classic]], [[domain/keno-xtreme-medium]],
[[domain/keno-xtreme-hard]], [[domain/keno-xtreme-easy]],
[[codebase/luma-keno]]. Rating gates:
[[domain/stake-rating-limits]].
Books/LUT units: [[domain/stake-engine-publish]].

This page is the algorithm. Do not paste a new max into JSON by hand.

## Identity

Pool **40**, draw **10**, picks **k = 1…10**. Hits `h` are
Hypergeometric(`N=40`, `K=10`, `n=k`):

```
P(h) = C(10,h) · C(30, k-h) / C(40,k)
```

One advertised multiplier `m[h]` per hit count. Off RTP is exact, no Monte Carlo:

```
RTP(k) = Σ_{h=0..k}  P(h) · m[h]
house edge = 1 − RTP
```

Fleet target is **RTP = 0.9650** (edge **3.50%**). Designed window for a
solved Off row is **0.9630–0.9655**, inside `MODE_RTP_BAND` (0.9628–0.9665)
and under the 0.967 per-mode cap. Cross-Mode spread over freely-tuned
certified modes must stay ≤ **0.50pp**.

RGS payout column is `int(round(m[h] * 100))` and must be a **multiple of
10** — so every advertised cell is on the **0.1× lattice**. One multiplier
per hit. Do not split miss weight to fake a finer RTP.

## What is locked vs what is solved

Per pick `k`, the generator takes three inputs and produces one row
`m[0]…m[k]`:

| Input | Who sets it | Why |
| --- | --- | --- |
| Zero prefix | Competitor HUD shape | Same first paying hit `f` as Keno Xtreme |
| Max `M = m[k]` | Designed `MAX_LADDER` | Product jackpot; must rise with `k` |
| RTP target | 0.9650 | House edge 3.50% |

Everything between `f` and `k−1` (the **body**) is solved so the identity
holds. Lowering `M` **increases** leftover for the body
(`leftover = 0.9650 − P(k)·M`); the peak gets smaller, mid cells get
fatter. Raising `M` does the opposite and can empty the body or blow the
window.

Maxes must be **strictly increasing** across picks (classic pick_1 lattice
max 2.6 is the floor under pick 2). A max that is not on a legal lattice
point is rejected — the generator raises `no legal progressive row under max`.

## Gates a row must pass

After snap, every Off row is graded by `base_stats` / `check_gates`:

| Gate | Local floor/cap | Why |
| --- | --- | --- |
| RTP window | 0.9630–0.9655 | Designed house edge ~3.5% |
| 0.1× lattice | `payout % 10 == 0` | RGS |
| Strictly increasing paying cells | `m[h] > m[h−1]` on paying hits | HUD reads as a ladder |
| Hit rate | ≥ 2.1% (dashboard 2%) | Non-zero win ≥ 1 in 50 |
| Base Mode STD | ≥ 0.62 (dashboard 0.60) | Leave display margin |
| ETL sum | ≤ 1.45 (3-Star 1.500) | Tail |

Fail closed. Change `M` or the zeros; never clamp after validation.

## Algorithm A — max-anchored geometric (Off `classic`, `medium`, `high`)

Used for classic, medium, and high picks **2–10**. Pick 1 is Algorithm C.
Code: `easy_off_classic.generate_classic_row`; medium/high pass their own
HUD zeros and `MAX_LADDER`. A single paying cell (Hard pick 2) is legal:
the max *is* the row.

1. **Lock** `M = MAX_LADDER[k]`. Keep HUD zeros. First paying hit is `f`.
2. **Shape.** Every paying cell grows by the **same factor** `r` toward the peak:

   ```
   m[h] = m_f · r^(h−f)     r = (M / m_f)^(1/(k−f))
   m[k] = M                 (held exact)
   ```

3. **Solve `m_f`** so `Σ P(h)·m[h] = 0.9650`.
   - Two paying cells (`k−f = 1`, e.g. pick 3): closed form
     `m_f = (0.9650 − P(k)·M) / P(f)`.
   - More cells: bisection on `m_f` (RTP is monotone in `m_f`).
4. **Snap** body cells to 0.1×. Keep `M` exact. Fix monotonicity
   (`+0.1` forward, `−0.1` back) if snap collided.
5. **Repair.** Deterministic coordinate descent: body cells in fixed
   order (highest `P(h)` first), try `±0.1, ±0.2, ±0.3`. Accept a nudge
   only if it strictly improves `|RTP − 0.9650|` and the step ratio stays
   inside a band of the ideal `r` (bands 2.5, then 4.0, then 8.0). Same
   input → same matrix, every run.

If no legal row exists under that `M`, the max is not lattice-legal.
Sweep `M` downward in 0.5× steps until the generator accepts.

Shipped classic max ladder (2026-09-01, picks 3–6 cut from the HUD
40/100/300/500 because those perfect-hit tops read too big):

```
2.6 / 5.4 / 17.5 / 30 / 75 / 200 / 600 / 750 / 900 / 1000
```

Pick 2 HUD max 5.00 has no in-window pair (1.7/5.0 = 0.9423, 1.8/5.0 =
0.9808). Snap is **5.4**. Pick 3 is a two-cell row: only
8.5 / 13 / 17.5 / 22 / 26.5 / 31 / 35.5 / 40 are legal; **17.5** is the
smallest that still steps ~×3 off the hit-2 cell.

Shipped medium max ladder (2026-09-02). HUD tops on picks 2–4 cannot ship
(lattice / ETL40 / generator reject):

```
3.2 / 9.4 / 60.3 / 174.9 / 450 / 650 / 750 / 2500 / 4000 / 5000
```

HUD pick 3 **75×** is 115% RTP and ETL40 0.911. 65.8× is the absolute
ETL40 ceiling (0.799); shipped **60.3** keeps margin. Pick 2 HUD 9.00
has the same no-pair exception as classic 5.00 → **9.4**. Pick 4 HUD
175.0 rejects; snap **174.9**.

Shipped high max ladder (2026-09-02). HUD picks 2–5 cannot ship
(RTP / ETL40 / generator reject). Picks 6–10 keep the HUD jackpots:

```
3.5 / 16.7 / 71.6 / 382.4 / 2297.8 / 6000 / 12500 / 25000 / 40000 / 50000
```

HUD pick 2 **20×** is 115% RTP; only **16.7** is in-window (single-cell
2/2). Pick 3 **500×** is ~614% RTP; highest legal **71.6**. Pick 4
**1000** → **382.4**. Pick 5 **2500** → **2297.8**. Geometric leftover-fill
lets pick 6 keep **6000** (old remainder-pack cut it to 3484.6).

### Worked row — classic pick 6

`P(6/6) ≈ 5.47e-5` (1 in 18,278). At `M = 200`:

```
leftover = 0.9650 − P(6)·200 ≈ 0.9541
```

Geometric fill of hits 3–5, snap + repair:

```
m = [0, 0, 0, 3.9, 14.8, 54.2, 200]
RTP = 0.964941    edge = 3.51%    step ≈ ×3.66–3.79
```

Same leftover identity at other shipped tops:

| k | M | P(k)·M | leftover to body | RTP |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 17.5 | 0.2126 | 0.7524 | 0.9641 |
| 4 | 30 | 0.0689 | 0.8961 | 0.9646 |
| 6 | 200 | 0.0109 | 0.9541 | 0.9649 |
| 10 | 1000 | ~0.000001 | ~0.9650 | 0.9650 |

A 10/10 is ~1 in 848 million, so pick 10's max is almost free RTP. Small
picks have fat perfect-hit probabilities (pick 3 is 1 in 82), so their
maxes **must** stay small or one cell eats the whole 0.965 budget
(`P(3)·100 = 1.21` RTP — illegal).

## Algorithm B — leftover-share fill (Off `low`)

Used for the Easy analogue. Same lock-max + HUD zeros, different body.

1. Lock `M` (Easy HUD max; pick 2 snaps 4.5 → 4.7).
2. `leftover = 0.9650 − P(k)·M`.
3. Give each body hit the **same RTP share** the competitor HUD spent there:

   ```
   share[h] = P(h)·HUD[h] / Σ_body P·HUD
   m[h]     = leftover · share[h] / P(h)
   ```

4. Snap 0.1×, hill-climb `±0.1` to minimise `|RTP − 0.9650|`.

This **does not** keep a constant step `r`. It copies the Easy HUD's
*allocation*, then retargets 99% RTP → 96.5%. Classic does **not** use
this — remainder-pack pooled leftover into the 2nd-best cell (e.g.
73 → 732 → 1000) and broke the progressive read.

## Algorithm C — pick_1 two-outcome lattice + miss-bonus close

`P(hit) = 10/40 = 0.25`, `P(miss) = 0.75`. Advertised pair on the 0.1× grid:

```
RTP_base = 0.75·m₀ + 0.25·m₁
```

Reachable base RTPs are multiples of **0.025**. Only **0.950** and **0.975**
exist near target. 0.975 busts the 0.967 cap. Dashboard Cross-Mode is
**0.50pp and includes every published mode** — a 0.950 pick_1 reads as
~1.50–1.62pp against the 0.965 fleet and fails certification.

The 1.5pp gap is closed by a third miss tier (not by moving picks 2–10
off 0.9650): 6 of 30 miss books pay `m₀ + 0.1` (1 in 5 misses). LUT RTP
becomes 0.9650. Advertised row stays the two-cell pair.

| risk | advertised | bonus miss | LUT RTP |
| --- | --- | ---: | ---: |
| classic | `[0.4, 2.6]` | 0.5× | 0.9650 |
| low | `[0.5, 2.3]` | 0.6× | 0.9650 |
| medium | `[0.2, 3.2]` | 0.3× | 0.9650 |
| high | `[0.1, 3.5]` | 0.2× | 0.9650 |

Earn pick_1 prices Lumen + Pulse in and uses a different pair
(`classic` `[0.5, 2.1]` → 0.9630).

## Volatility is derived, not solved

Dashboard LOW / MEDIUM / HIGH / EXTREME is **base stddev**, not max.
A top cell contributes `P(k)·(M − RTP)²` to variance. `P(k)` falls
~15× per pick while `M` rises, so that product **peaks mid-ladder**
(high pick 5–6) and is ~0 at pick 10.

Once zeros, max, and RTP 0.9650 are locked, the geometric body is
unique. High pick 10 at 50,000× still rates MEDIUM (std ~11): the
jackpot has **no part** in the variance (top share ~2.5%). Body nudges
move std by <0.1. Extra zeros (first pay h=5) only reach std ~13.
Do **not** retarget 96.5% or invent a second shape to chase a label on
picks 9–10.

The lever that *does* move the dashboard is a smaller max on picks
where `P(k)·M²` still binds — high 5–8. Those sit on the **std-18.3
envelope** (900 / 2200 / 5500 / 6100) so they rate HIGH, not EXTREME.
`easy_off_high.py` asserts `std ≤ 18.5` on those four picks. Low risk
stays LOW (std 0.8–2.0) because the HUD body is frequent and small.

## Earn and buy are not this generator

Off has no Lumen/Pulse — the posted table **is** the wallet multiplier.
Earn advertises a cheaper row so Lumen ×2 × Pulse ×2 can settle the
How-to at or above Off. Buy JSON tops pin to `min(Off max, dashboard cap / (2·cost))`.
Re-solve Earn/buy with `--earn-<risk>` / `--buy-<risk>` after an Off max
cut; their gates are one-directional (must not sit *below* Off on
jackpot picks, must not *raise* Off on buy JSON).

## How to change a max and republish

1. Put the new `M` in `MAX_LADDER[k]` (`easy_off_classic.py` /
   `easy_off_medium.py` / `easy_off_high.py`). Confirm
   `generate_classic_row(k, hud, mx)` returns a row (else pick the next
   legal lattice neighbor).
2. Bake that row into `CLASSIC_OFF` / `MEDIUM_OFF` / `HIGH_OFF`. Import
   validates bake == generator.
3. `python3 solve_paytables.py --off-<risk>` (math + web `risks.<risk>`).
4. If Earn/buy should follow: update `CLASSIC_EARN_TOP` /
   `MEDIUM_EARN_TOP` / `HIGH_EARN_TOP`, then `--earn-<risk>` and
   `--buy-<risk>`.
5. `python3 run_classic.py` / `run_medium.py` / `run_high.py` for books/LUTs.
6. `python3 export_chart.py risks <risk>` (and earn/buy10/buy100 if patched).
7. `rgs_verification`, `npm run verify-front-math`, `npm run par-sheet`.

Do not regenerate all 160 modes unless the change crosses risks.

## What this algorithm is not

- Not the Rust optimizer. Weights stay exact `C(10,h)·C(30,k−h)`.
- Not water-fill / remainder-pack (that is the old classic/medium/high
  bodies before the geometric bake).
- Not a Monte Carlo RTP. Keno RTP is a finite sum.
- Not a client roll. `/wallet/play` samples a published book; the
  frontend only reconstructs a draw for the booked hit count.
