# Keno events and frontend reconstruction

`/wallet/play` returns `book.events`. Anything not in events cannot be
shown as authoritative. Wallet credit uses book-root `payoutMultiplier`,
not an amount the client computes from spots.

## Required event sequence

Custom types plus standard win close-out. Emit immediately after each
state change.

```json
[
  {
    "index": 0,
    "type": "kenoStart",
    "picksCount": 10,
    "drawnCount": 20,
    "poolSize": 80,
    "paytable": [0, 0, 0, 1, 2.5, 5, 15, 50, 200, 500, 1000],
    "lumenMarked": true,
    "lumenBoost": 2,
    "pulseBoost": 2
  },
  {
    "index": 1,
    "type": "kenoCatch",
    "hits": 8,
    "mainHits": 7,
    "multiplier": 100,
    "lumenHit": true,
    "lumenBoost": 2,
    "extrasOpened": true,
    "extraHits": 1,
    "extraReason": "lumen",
    "pulse": 2
  },
  { "index": 2, "type": "setWin", "amount": 10000, "winLevel": 5 },
  { "index": 3, "type": "setTotalWin", "amount": 10000 },
  { "index": 4, "type": "finalWin", "amount": 10000 }
]
```

`amount` on win events is `int(round(multiplier * 100))` — same units as
`payoutMultiplier` (100× → `10000`). `paytable[h]` is the 0.1× chart
**before** Lumen. Wallet credit is book-root `payoutMultiplier`, which must
match LUT column 3 and `kenoCatch.multiplier`. Total hits (main + extra)
select the paytable row; Lumen then multiplies a paying row.

Do **not** emit slot `reveal` boards. Do **not** omit `finalWin` (tower
omits it to keep the round open; keno must close).

## Do not put player spots or a fixed draw in the book

A fixed 20-ball list in the book is only correct for one pick set. The
RGS cannot receive the player's card.

Allowed in events: `picksCount`, `hits` (total), `mainHits`, `lumenMarked`,
`lumenHit`, `lumenBoost`, `extrasOpened`, `extraHits`, `extraReason`,
multipliers, paytable row, book `id`.

Forbidden as source of truth: `pickedNumbers`, `drawnNumbers` used to
compute the payout on the client.

## Reconstruction (frontend)

Reconstruct the **main ten** from `mainHits`, then two extras from
`extraHits` if `extrasOpened`. Seed `book.id`. Same book + picks → same
animation.

## Lumen mark

Lumen is always one of the main 10. Do **not** put `lumenNumber` in the
book. Book `lumenHit` only. `P(lumenHit | mainHits=h) = h / 10`.

## Off vs Earn

Two published charts, same house edge:

| Sidebar | Mode | Math |
| --- | --- | --- |
| Off | `{risk}_pick_{k}` | Table only. `lumenMarked: false`. Criteria `hits_{h}`. |
| Earn | `{risk}_pick_{k}_earn` | Lumen + extras + multiplier. Separate `earn` paytable. |

Play payload `mode` is the only switch. Off books must not mark Lumen or
open extras. Earn books use the event fields below.

## Lumen multiplier

Earn only. If `lumenHit` and the table at **total** hits already pays,
multiply by `LUMEN_BOOST`: classic/low/**medium ×2**, high ×5. Medium is
×2 so Earn pick_1 stays inside 0.50pp of Off 0.950. Lumen does **not**
rescue a 0× row. `kenoStart.lumenBoost` is the potential (always the
risk factor, or 1 on Off). `kenoCatch.lumenBoost` is 1 or the applied
factor. `kenoCatch.multiplier` / LUT column 3 / book-root
`payoutMultiplier` are the settled amount (`lumen_pay`). The client
must **not** re-multiply.

## Extra lights

Earn only. Main draw is still 10. Extras are 0 or 2 more from the remaining 30.
Open on first match (no Buy yet):

1. `lumenHit` → `extraReason: lumen`
2. pick `k >= 4` and `mainHits == k - 1` → `nearMiss`
3. `mainHits >= 2` and a luck roll (`EXTRA_CHANCE`: 16/10/7/4% by risk)
   → `natural`

`hits` on `kenoCatch` is **total** (`mainHits + extraHits`) and is the
paytable row. Pause after the tenth light.

Criteria: `hits_{h}_lumen_{0|1}_extra_{0|1}_{none|lumen|near|luck}_{eh}_pulse_{0|1}`.

## Pulse ×2

Earn only. Independent of extras: **10%** of Earn books apply Pulse ×2
after Lumen. Pulse does **not** rescue a 0× row. Off books never roll it.
`kenoStart.pulseBoost` is 2 on Earn / 1 on Off. `kenoCatch.pulse` is 1 or 2
(applied). Wallet `payoutMultiplier` already includes it.

`num_sim_args` is `book_count_for_picks(k)` (pick_1=6, pick_5=52,
pick_10=118). Cross-Mode is over all 80 published modes.

## Play / wallet

1. Player selects k numbers (client state only).
2. `POST /wallet/play` `{ amount, sessionID, mode: "classic_pick_k" }`
   or `"classic_pick_k_earn"`.
3. Debit = `amount * BetMode.cost` (cost is 1.0).
4. Animate reconstructed draw from `kenoCatch.mainHits` + extras.
5. Round auto-closes; credit from `payoutMultiplier`.

No `/wallet/end-round`. `auto_close_disabled=False`.

Amounts in the wallet API are 6-decimal integers (`1000000` = $1). That
is separate from book multipliers (×100).
