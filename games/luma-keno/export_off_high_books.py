"""Replace Off high books + paytable rows from the certified math tables."""
from __future__ import annotations

import json
from math import comb
from pathlib import Path

from keno_pick_one import off_outcomes, off_pay, off_weight

HERE = Path("/workspace")
PAY = json.loads((HERE / "paytables.json").read_text())
BOOKS = json.loads((HERE / "keno-books.json").read_text())
FRONT_PAY = json.loads((HERE / "keno-paytables-front.json").read_text())
POOL = 40


def export_off_mode(k: int, paytable: list[float]) -> dict:
    rows = []
    for i, spin in enumerate(off_outcomes(k)):
        base = off_pay(spin, paytable)
        payout_int = int(round(base * 100))
        weight = off_weight(k, spin)
        rows.append(
            {
                "id": i,
                "hits": spin.main_hits,
                "mainHits": spin.main_hits,
                "lumenHit": False,
                "lumenBoost": 1.0,
                "extrasOpened": False,
                "extraHits": 0,
                "extraReason": None,
                "pulse": 1.0,
                "pulseRolled": False,
                "missBonus": bool(spin.miss_bonus),
                "weight": int(weight),
                "payout": payout_int,
            }
        )
    total = sum(r["weight"] for r in rows)
    expect = comb(POOL, k)
    assert total == expect, f"high_pick_{k} weight {total} != {expect}"
    rtp = sum(r["weight"] * r["payout"] for r in rows) / (total * 100)
    return {"cost": 1.0, "rtp": rtp, "books": rows}


def main() -> None:
    FRONT_PAY["risks"]["high"] = PAY["risks"]["high"]
    print("risks.high tops", {k: max(v) for k, v in PAY["risks"]["high"].items()})
    for k_s, row in PAY["risks"]["high"].items():
        k = int(k_s)
        name = f"high_pick_{k}"
        mode = export_off_mode(k, row)
        BOOKS["modes"][name] = mode
        max_pay = max(r["payout"] for r in mode["books"])
        print(
            f"{name:20s} rtp={mode['rtp']:.4f} books={len(mode['books']):3d} "
            f"how_to={max_pay / 100:.1f}x"
        )
    (HERE / "keno-books.json").write_text(json.dumps(BOOKS, indent=2) + "\n")
    (HERE / "keno-paytables-front.json").write_text(
        json.dumps(FRONT_PAY, indent=2) + "\n"
    )
    print("wrote keno-books.json and keno-paytables-front.json")


if __name__ == "__main__":
    main()
