"""Replace Buy medium books + paytable rows from the certified math tables."""
from __future__ import annotations

import json
from pathlib import Path

from keno_pick_one import (
    BUY_SUFFIXES,
    PULSE_BOOST,
    REASON_TO_EVENT,
    lumen_boost_applied,
    lumen_placed_on_pick,
    paying_from_table,
    pulse_boost_applied,
    settle_pay,
    spin_outcomes,
    spin_weight,
    weight_total,
)

HERE = Path("/workspace")
PAY = json.loads((HERE / "paytables.json").read_text())
BOOKS = json.loads((HERE / "keno-books.json").read_text())
FRONT_PAY = json.loads((HERE / "keno-paytables-front.json").read_text())


def export_buy_mode(k: int, risk: str, paytable: list[float], buy: str, cost: float) -> dict:
    placed = lumen_placed_on_pick(buy, k)
    paying = paying_from_table(paytable)
    rows = []
    for i, spin in enumerate(
        spin_outcomes(k, paying=paying, bought=True, placed=placed)
    ):
        base = paytable[spin.total_hits]
        payout_int = int(round(settle_pay(base, spin.lumen_hit, spin.pulse, risk, buy) * 100))
        weight = spin_weight(
            k, spin, risk, paying=paying, bought=True, placed=placed
        )
        after_lumen = lumen_boost_applied(base, spin.lumen_hit, risk, buy)
        rows.append(
            {
                "id": i,
                "hits": spin.total_hits,
                "mainHits": spin.main_hits,
                "lumenHit": spin.lumen_hit,
                "lumenBoost": after_lumen,
                "extrasOpened": spin.extras,
                "extraHits": spin.extra_hits if spin.extras else 0,
                "extraReason": REASON_TO_EVENT[spin.extra_reason],
                "pulse": pulse_boost_applied(
                    settle_pay(base, spin.lumen_hit, False, risk, buy), spin.pulse, risk
                ),
                "pulseRolled": bool(spin.pulse),
                "missBonus": bool(spin.miss_bonus),
                "weight": int(weight),
                "payout": payout_int,
            }
        )
    total = sum(r["weight"] for r in rows)
    expect = weight_total(k, placed=placed)
    assert total == expect, f"medium_pick_{k}_{buy} weight {total} != {expect}"
    rtp = sum(r["weight"] * r["payout"] for r in rows) / (total * 100 * cost)
    return {"cost": cost, "rtp": rtp, "books": rows}


def main() -> None:
    pulse = PULSE_BOOST["medium"]
    for buy, cost in BUY_SUFFIXES.items():
        FRONT_PAY[buy]["medium"] = PAY[buy]["medium"]
        print(f"{buy}.medium advertised tops", {k: max(v) for k, v in PAY[buy]["medium"].items()})
        for k_s, row in PAY[buy]["medium"].items():
            k = int(k_s)
            name = f"medium_pick_{k}_{buy}"
            mode = export_buy_mode(k, "medium", row, buy, cost)
            BOOKS["modes"][name] = mode
            max_pay = max(r["payout"] for r in mode["books"])
            json_top = max(row)
            of_buy = max_pay / 100.0 / cost
            vs_debit = of_buy
            print(
                f"{name:22s} rtp={mode['rtp']:.4f} books={len(mode['books']):3d} "
                f"json={json_top:.1f} of_buy_how={of_buy:.1f}x "
                f"(json*pulse={json_top * pulse:.1f}) vs_debit={vs_debit:.1f}x "
                f"max_base={max_pay/100:.1f}x placed={lumen_placed_on_pick(buy, k)}"
            )
    (HERE / "keno-books.json").write_text(json.dumps(BOOKS, indent=2) + "\n")
    (HERE / "keno-paytables-front.json").write_text(
        json.dumps(FRONT_PAY, indent=2) + "\n"
    )
    print("wrote keno-books.json and keno-paytables-front.json")


if __name__ == "__main__":
    main()
