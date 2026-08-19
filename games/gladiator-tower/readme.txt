# Gladiator Tower

BitKong-style multi-step cashout climb. The player climbs a tower row by row;
each row has fixed columns and safe tiles (the rest are mines). A safe pick
advances the running coefficient by that row's step (× any bonus); a mine ends
the round with payout 0. The player can cash out after any cleared row, or
cancel to close the session and return the bet to balance.

Rules
-----
  * Safe  → coefficient multiplies by row step (and any collected bonus)
  * Mine  → round ends, payout 0 (stake stays lost)
  * Cash out after any cleared row → lock the current coefficient
  * Cancel → close session and return the bet to balance

Bonus rows (rows 3 / 6 / 9, 0-indexed 2 / 5 / 8):
    row 3 → ×2  (1-in-10)   P appears = 10.0%
    row 6 → ×5  (1-in-7)    P appears = 14.29%
    row 9 → ×10 (1-in-5)    P appears = 20.0%

Each bonus row rolls independently with ``rng.random() < 1/N`` (docs
``P_exists = 1/N``). Business logic (roll / place) lives ONLY in the math SDK
(``game_calculations.py`` roll_bonus / pick_bonus_cell + ``session.py``
_resolve_row_bonus). The web client never rolls or places a bonus — it only
*applies* a bonus the server pre-resolves into
``session.rowBonuses[row] = {cellIndex, multiplier}``.

Session engine (``session.py``)
-----------------------------
  * ``start_session(difficulty, bet_amount, mode, rng, ...)`` — opens an
    ACTIVE session, draws (or accepts) the mine layout, pre-resolves every
    bonus row, and returns a ``TowerSession``.
  * ``pick_tile(session, row, tile, *, apply_bonuses=...)`` — resolves one
    row; advances the coefficient or ends on a mine. Auto-cashes out at top.
  * ``cash_out(session)`` — locks the win from current state (ladder ×
    collected bonuses), capped at ``max_payout``.
  * ``resolve_row_bonus`` / ``resolved_row_bonuses`` — public API to hand
    pre-resolved bonus placements to the client.

Stake session flow
-----------------
1. Start Session → ``/wallet/play`` mode ``easy`` (or medium / hard / …)
   Book: ``sessionStart`` + ``mineLayout``, book root ``payoutMultiplier`` = 100
   (1×), ``active: true`` (``auto_close_disabled``). Initial UI: 1×, payout = bet.
2. Each pick → resolve locally + ``/bet/event`` climb blob.
3. Refresh / reload → ``/wallet/authenticate``; restore active round from
   ``round.event`` and/or localStorage.
4. Cash out / top cleared → ``/wallet/end-round`` →
   ``/wallet/play({difficulty}_{n} | {difficulty}_p{payout×100})`` →
   ``/wallet/end-round``. Credits the climb multiplier from the settle book.
5. Mine hit → ``/wallet/end-round`` → ``/wallet/play({difficulty}_loss)`` →
   ``/wallet/end-round``. Net: stake stays lost.
6. Cancel → ``/wallet/end-round`` only (session book is 1× → bet returns).

Published modes
---------------
Session open (Start — initial 1×):
    easy, medium, hard, extreme, nightmare

Settle (after session close):
    {difficulty}_loss            → payout ≈ 0
    {difficulty}_1 … _{rows}     → payout ≈ ladder at that depth
    {difficulty}_p{payout×100}   → bonus-aware settle (ladder × bonus product)

House edge + RTP
----------------
Fair per-row odds = cols / win_count. Depth-scaled house edge:

    BASE_HOUSE_EDGE = 0.01
    EDGE_GROWTH     = 0.002
    step[i] = fair * (1 - (0.01 + i * 0.002))
    coefficient = floor(coefficient * step * bonusMultiplier * 10) / 10

Published ``sessionRtp`` = play-to-top, random pick, bonuses ignored:
    RTP = (winChance) ** rows × topMultiplier

Win cap / row limit
-------------------
Every mode uses ``maxWinning = $10,000`` (``DEFAULT_MAX_PAYOUT``). Multipliers
are auto-calculated from fair odds + row count; ``maxWinning`` only truncates
playable height and hard-caps cashout (it does not reshape the ladder).

Publish note — ERR_MATH_OUTSIDE_RANGE
------------------------------------
Constant single-payout LUTs fail Stake stats. Books include ~1% ±0.1× jitter
so each mode has ≥3 distinct payouts (e.g. session open mostly 100, rare
90 / 110).

Run
---
    cd math && PYTHONPATH=".:games/gladiator-tower" python3 games/gladiator-tower/run.py

Exports ``library/configs/math_config.json``. Upload the contents of
``library/publish_files/`` to Stake Engine as one bundle.
