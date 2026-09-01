"""Replace Earn medium books + paytable rows from the certified math tables."""
from __future__ import annotations

import json
from pathlib import Path

from keno_pick_one import (
    REASON_TO_EVENT,
    lumen_boost_applied,
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


def export_earn_mode(k: int, risk: str, paytable: list[float]) -> dict:
    paying = paying_from_table(paytable)
    rows = []
    for i, spin in enumerate(spin_outcomes(k, paying=paying, bought=False, placed=False)):
        base = paytable[spin.total_hits]
        payout_int = int(round(settle_pay(base, spin.lumen_hit, spin.pulse, risk, None) * 100))
        weight = spin_weight(k, spin, risk, paying=paying, bought=False, placed=False)
        after_lumen = lumen_boost_applied(base, spin.lumen_hit, risk, None)
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
                    settle_pay(base, spin.lumen_hit, False, risk, None), spin.pulse, risk
                ),
                "pulseRolled": bool(spin.pulse),
                "missBonus": bool(spin.miss_bonus),
                "weight": int(weight),
                "payout": payout_int,
            }
        )
    total = sum(r["weight"] for r in rows)
    expect = weight_total(k, placed=False)
    assert total == expect, f"medium_pick_{k}_earn medium pick {k} weight {total} != {expect}"
    rtp = sum(r["weight"] * r["payout"] for r in rows) / (total * 100)
    return {"cost": 1.0, "rtp": rtp, "books": rows}


def main() -> None:
    FRONT_PAY["earn"]["medium"] = PAY["earn"]["medium"]
    print(
        "earn.medium advertised tops",
        {k: max(v) for k, v in PAY["earn"]["medium"].items()},
    )
    for k_s, row in PAY["earn"]["medium"].items():
        k = int(k_s)
        name = f"medium_pick_{k}_earn"
        mode = export_earn_mode(k, "medium", row)
        BOOKS["modes"][name] = mode
        max_pay = max(r["payout"] for r in mode["books"])
        print(
            f"{name:20s} rtp={mode['rtp']:.4f} books={len(mode['books']):3d} "
            f"max_payout_cents={max_pay} how_to={max_pay/100:.1f}x"
        )
    (HERE / "keno-books.json").write_text(json.dumps(BOOKS, indent=2) + "\n")
    (HERE / "keno-paytables-front.json").write_text(
        json.dumps(FRONT_PAY, indent=2) + "\n"
    )
    print("wrote keno-books.json and keno-paytables-front.json")


if __name__ == "__main__":
    main()
