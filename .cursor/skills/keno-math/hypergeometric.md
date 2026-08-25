# Keno hypergeometric math

Pool `N=80`, draw `K=20`, player picks `n=k` (usually 1..10). Hits
`X = |picks ∩ drawn|` is Hypergeometric(N, K, n):

```
P(X = h) = C(K, h) * C(N - K, n - h) / C(N, n)
         = C(20, h) * C(60, k - h) / C(80, k)
```

Legal h: `max(0, k - 60) .. min(k, 20)`. For k ≤ 10 this is `0 .. k`.

## Integer LUT weights

Do not store floats. Weight for hit h (uint64):

```
w(h) = C(20, h) * C(60, k - h)
```

Then `Σ_h w(h) = C(80, k)`, and `P(h) = w(h) / C(80, k)`.

Python:

```python
from math import comb

def hit_weight(k: int, h: int, drawn: int = 20, pool: int = 80) -> int:
    rest = pool - drawn
    if h < 0 or h > k or k - h > rest:
        return 0
    return comb(drawn, h) * comb(rest, k - h)
```

Write LUT rows as `id,weight,payout` with `payout = int(round(m * 100))`.
One row per hit count. Do **not** split a hit's weight across two prizes
(luma-keno pick_1 remainder 24+6 paid 0.6× and 0.7× for the same miss —
that failed Base Mode STD and showed two history amounts).

luma-keno uses `N=40`, `K=10` (`rest=30`). Same formulas; `w(h) =
C(10,h)*C(30,k-h)`, `Σ w = C(40,k)`.

## RTP

```
RTP(k) = Σ_h P(X=h) * m(k, h) = Σ_h w(h) * m(k, h) / C(80, k)
```

Target the same RTP for every k (see SKILL.md — 5 pt mode gap). After
rounding multipliers to 0.1×, recompute this sum; do not trust the
pre-round budget.

## Worked P(X=k) for k=10

`C(80,10) = 1_646_492_110`, `C(20,10) = 184_756`,
`P(10 hits) = 184756 / 1646492110 ≈ 1.1215e-4` (about 1 in 8,915).

A 10,000× top prize at that probability is **~1.12 RTP by itself**. Illegal
for a ~96–97% game. Solve `m_max = budget_max / P(10)` from leftover RTP
after the rest of the table.

## What not to simulate

- Drawing 20 balls in `run_spin` and counting hits against random picks
  — that estimates `P(h)` with noise and needs huge N for the tail.
- Assigning weight=1 to every book then optimizing to target RTP — the
  optimizer will not recover hypergeometric odds.

Force `h` from `criteria` and stamp `w(h)` on the LUT.
