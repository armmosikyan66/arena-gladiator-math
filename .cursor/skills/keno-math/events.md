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
    "paytable": [0, 0, 0, 1, 2.5, 5, 15, 50, 200, 500, 1000]
  },
  {
    "index": 1,
    "type": "kenoCatch",
    "hits": 7,
    "multiplier": 50
  },
  { "index": 2, "type": "setWin", "amount": 5000, "winLevel": 5 },
  { "index": 3, "type": "setTotalWin", "amount": 5000 },
  { "index": 4, "type": "finalWin", "amount": 5000 }
]
```

`amount` on win events is `int(round(multiplier * 100))` — same units as
`payoutMultiplier` (50× → `5000`). `paytable[h]` is the 0.1× chart.
Wallet credit is book-root `payoutMultiplier`, which must match LUT
column 3 and `kenoCatch.multiplier`. One multiplier per hit count —
`paytable[h]` and the sampled book agree.

Do **not** emit slot `reveal` boards. Do **not** omit `finalWin` (tower
omits it to keep the round open; keno must close).

## Do not put player spots or a fixed draw in the book

A fixed 20-ball list in the book is only correct for one pick set. The
RGS cannot receive the player's card.

Allowed in events: `picksCount`, `hits`, multipliers, paytable row, book
`id` (already on the book root).

Forbidden as source of truth: `pickedNumbers`, `drawnNumbers` used to
compute the payout on the client.

## Reconstruction (frontend)

Given player spots `P` (`|P|=k`), book `hits=h`, `drawnCount=20`,
`poolSize=80`, seed `book.id`:

```python
from random import Random

def reconstruct_draw(picks, hits, drawn=20, pool=80, seed=1):
    rng = Random(seed)
    picks = list(picks)
    caught = rng.sample(picks, hits)
    rest = [n for n in range(1, pool + 1) if n not in set(picks)]
    missed = rng.sample(rest, drawn - hits)
    draw = caught + missed
    rng.shuffle(draw)
    return draw  # 20 numbers; exactly `hits` overlap picks
```

Reconnect / refresh: same book id + same picks → same animation.
Changing picks after play is a UI bug; the paid `hits` stay.

## Play / wallet

1. Player selects k numbers (client state only).
2. `POST /wallet/play` `{ amount, sessionID, mode: "pick_k" }`.
3. Debit = `amount * BetMode.cost` (cost is 1.0).
4. Animate reconstructed draw from `kenoCatch.hits`.
5. Round auto-closes; credit from `payoutMultiplier`.

No `/wallet/end-round`. `auto_close_disabled=False`.

Amounts in the wallet API are 6-decimal integers (`1000000` = $1). That
is separate from book multipliers (×100).
