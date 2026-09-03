#!/usr/bin/env python3
"""Apply Buy100 dominance fix under HARD wiki gates (MAX_PAYOUT_ABS buy100=90k → JSON≤450).

Run from games/luma-keno on the Mac host:
  ../../env/bin/python /path/to/apply_buy100_dominance_fix.py

Does NOT touch buy10 polish, web/, or git push.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
from dataclasses import replace
from textwrap import dedent

ROOT = pathlib.Path(__file__).resolve().parent
# Allow running from copied location or from luma-keno itself
if (ROOT / "buy_bonus.py").exists():
    GAME = ROOT
elif (pathlib.Path.cwd() / "buy_bonus.py").exists():
    GAME = pathlib.Path.cwd()
else:
    GAME = pathlib.Path("/Users/armanmosikyan/Documents/keno-game/math/games/luma-keno")

sys.path.insert(0, str(GAME))
os_chdir = True
import os
os.chdir(GAME)

from buy_bonus import (  # noqa: E402
    BUY_COSTS,
    BuyRiskConfig,
    generate_buy_chart,
    legal,
    retarget_buy_row,
    to_json_row,
    zero_mask_for,
)
from keno_pick_one import lumen_placed_on_pick, settled_stats  # noqa: E402

# ---------------------------------------------------------------------------
# Target ladders (wiki: pin deep classic/med/high buy100 tops at full 450)
# ---------------------------------------------------------------------------

CLASSIC_BUY100_P4 = [0.0, 0.0, 0.7, 1.6, 16.0]  # ≠ buy10 [0,0,0.4,2.2,18]

MED_LADDER_100 = {
    2: 2.6,
    3: 5.4,
    4: 14.0,  # diverge top from buy10's 12
    5: 40.0,
    6: 150.0,
    7: 250.0,
    8: 350.0,
    9: 420.0,
    10: 450.0,
}
# If pick4@14 fails, fall back to same top 12 with different body
MED_LADDER_100_FALLBACKS = [
    {**MED_LADDER_100, 4: 12.0, 6: 140.0, 7: 220.0, 8: 320.0, 9: 400.0},
    {**MED_LADDER_100, 4: 12.0, 6: 120.0, 7: 200.0, 8: 300.0, 9: 380.0, 10: 450.0},
    {2: 2.6, 3: 5.4, 4: 12.0, 5: 40.0, 6: 120.0, 7: 180.0, 8: 280.0, 9: 380.0, 10: 450.0},
    {2: 2.6, 3: 5.4, 4: 12.0, 5: 40.0, 6: 120.0, 7: 160.0, 8: 250.0, 9: 350.0, 10: 450.0},
]

HI_LADDER_100 = {
    2: 2.6,
    3: 5.4,
    4: 25.0,  # diverge from buy10 22
    5: 80.0,
    6: 160.0,
    7: 250.0,
    8: 350.0,
    9: 420.0,
    10: 450.0,
}
HI_LADDER_100_FALLBACKS = [
    {**HI_LADDER_100, 4: 20.0, 6: 150.0, 7: 220.0, 8: 320.0, 9: 400.0},
    {2: 2.6, 3: 5.4, 4: 20.0, 5: 80.0, 6: 140.0, 7: 200.0, 8: 300.0, 9: 380.0, 10: 450.0},
    {2: 2.6, 3: 5.4, 4: 22.0, 5: 80.0, 6: 130.0, 7: 180.0, 8: 280.0, 9: 360.0, 10: 450.0},
    {2: 2.6, 3: 5.4, 4: 22.0, 5: 80.0, 6: 120.0, 7: 160.0, 8: 250.0, 9: 320.0, 10: 450.0},
    # last resorts still try pick10=450
    {2: 2.6, 3: 5.4, 4: 22.0, 5: 80.0, 6: 120.0, 7: 160.0, 8: 220.0, 9: 300.0, 10: 450.0},
    {2: 2.6, 3: 5.4, 4: 22.0, 5: 80.0, 6: 120.0, 7: 160.0, 8: 200.0, 9: 280.0, 10: 420.0},
]

LOW_BUY100_SEED = {
    # Same tops as buy10; different mid allocation (dominance via strip ≠)
    2: [0.0, 0.3, 2.6],
    3: [0.0, 0.3, 1.2, 2.6],
    4: [0.0, 0.3, 0.8, 2.0, 8.0],
    5: [0.0, 0.0, 0.4, 1.2, 5.5, 40.0],
    6: [0.0, 0.0, 0.5, 0.9, 2.2, 11.0, 60.0],
    7: [0.0, 0.0, 0.0, 1.0, 1.8, 4.8, 22.0, 120.0],
    8: [0.0, 0.0, 0.0, 0.8, 1.4, 3.6, 6.5, 22.0, 160.0],
    9: [0.0, 0.0, 0.0, 0.0, 1.4, 2.8, 6.0, 10.5, 24.0, 180.0],
    10: [0.0, 0.0, 0.0, 0.0, 1.0, 2.0, 4.5, 8.0, 12.0, 28.0, 200.0],
}


def show(tag, risk, buy, chart):
    cost = BUY_COSTS[buy]
    print(f"\n## {tag}")
    for k, row in sorted(chart.items()):
        crow = [m / cost for m in row]
        placed = lumen_placed_on_pick(buy, k)
        s = settled_stats(risk, k, crow, bought=True, placed=placed, cost=cost, buy=buy)
        print(
            f"  p{k}: top={row[-1]} how={s['max_m']:.0f} rtp={s['rtp']:.4f} "
            f"hr={s['hit_rate']:.4f} {row}"
        )


def solve_chart(cfg: BuyRiskConfig, buy: str, ladder: dict | None = None) -> dict[int, list[float]]:
    if ladder is not None:
        cfg = replace(
            cfg,
            json_max_ladder_buy100=ladder,
            baked={"buy10": cfg.baked.get("buy10", {}), "buy100": {}},
            prefer_exact_baked=False,
            climb_guards=max(cfg.climb_guards, 300),
        )
    else:
        cfg = replace(
            cfg,
            baked={"buy10": cfg.baked.get("buy10", {}), "buy100": {}},
            prefer_exact_baked=False,
            climb_guards=max(cfg.climb_guards, 300),
        )
    chart = {}
    for k in range(2, 11):
        crow = retarget_buy_row(cfg, k, buy)
        chart[k] = to_json_row(crow, BUY_COSTS[buy])
    return chart


def try_ladders(base_cfg: BuyRiskConfig, risk: str, primary: dict, fallbacks: list[dict]):
    errors = []
    for lad in [primary, *fallbacks]:
        try:
            chart = solve_chart(base_cfg, "buy100", lad)
            print(f"{risk} SUCCESS ladder", {k: lad[k] for k in range(4, 11)})
            return chart, lad
        except Exception as e:
            errors.append((lad, str(e)))
            print(f"{risk} fail { {k: lad.get(k) for k in range(4, 11)} } -> {e}")
    raise RuntimeError(f"{risk}: no legal buy100 ladder\n" + "\n".join(f"  {a}: {b}" for a, b in errors[-5:]))


def format_dict_int_list(name: str, chart: dict[int, list[float]]) -> str:
    lines = [f"{name}: dict[int, list[float]] = {{"]
    for k in sorted(chart):
        row = ", ".join(f"{x:.1f}" if isinstance(x, float) else str(x) for x in chart[k])
        # normalize ints like 2.0 -> 2.0 kept for consistency with existing style
        cells = []
        for x in chart[k]:
            cells.append(f"{float(x):.1f}")
        lines.append(f"    {k}: [{', '.join(cells)}],")
    lines.append("}")
    return "\n".join(lines)


def format_ladder(name: str, lad: dict[int, float]) -> str:
    lines = [f"{name} = {{"]
    for k in sorted(lad):
        lines.append(f"    {k}: {float(lad[k])},")
    lines.append("}")
    return "\n".join(lines)


def replace_assignment(src: str, name: str, new_block: str) -> str:
    """Replace `NAME = { ... }` or `NAME: dict... = { ... }` top-level assignment."""
    pattern = re.compile(
        rf"^({re.escape(name)}(?:\s*:\s*dict\[[^\]]+\]\s*)?\s*=\s*\{{)(.*?)(^\}})",
        re.M | re.S,
    )
    m = pattern.search(src)
    if not m:
        raise KeyError(f"assignment {name} not found")
    # new_block includes name + braces
    return src[: m.start()] + new_block + src[m.end() :]


def patch_file(path: pathlib.Path, replacements: dict[str, str]):
    text = path.read_text()
    for name, block in replacements.items():
        text = replace_assignment(text, name, block)
    path.write_text(text)
    print(f"patched {path.name}: {', '.join(replacements)}")


def main():
    print("GAME=", GAME)
    paytables_path = GAME / "paytables.json"
    before = json.loads(paytables_path.read_text())

    # Snapshot before
    print("\n=== BEFORE pick4 / pick10 ===")
    for risk in ("classic", "low", "medium", "high"):
        for k in ("4", "10"):
            print(f"  {risk} buy10[{k}]={before['buy10'][risk][k]}")
            print(f"  {risk} buy100[{k}]={before['buy100'][risk][k]}")

    from easy_buy_classic import CLASSIC_BUY_CONFIG, EASY_BUY_CLASSIC, EASY_BUY_CLASSIC_BUY100, EASY_BUY_CLASSIC_PICK1
    from easy_buy_medium import MEDIUM_BUY_CONFIG, EASY_BUY_MEDIUM, EASY_BUY_MEDIUM_PICK1
    from easy_buy_high import HIGH_BUY_CONFIG, EASY_BUY_HIGH, EASY_BUY_HIGH_PICK1
    from easy_buy_low import LOW_BUY_CONFIG, EASY_BUY_LOW, EASY_BUY_LOW_PICK1

    # --- classic: keep deep 450 via apply_payout_cap; diverge pick4 + re-solve body ---
    cl_cfg = replace(
        CLASSIC_BUY_CONFIG,
        baked={
            "buy10": EASY_BUY_CLASSIC,
            "buy100": {**EASY_BUY_CLASSIC_BUY100, 4: CLASSIC_BUY100_P4},
        },
        prefer_exact_baked=True,
    )
    # Force re-solve buy100 with empty bake except we seed pick4 preference via ladder
    # Classic uses shared ladder + cap → deep tops already 450. Rebuild all buy100.
    cl_chart = {}
    # Prefer exact seeded pick4 if legal; else retarget
    cost = 100.0
    for k in range(2, 11):
        if k == 4:
            crow = [m / cost for m in CLASSIC_BUY100_P4]
            mask = zero_mask_for(cl_cfg, k, "buy100")
            if legal(cl_cfg, k, mask, crow, crow[k], cost, "buy100"):
                cl_chart[k] = CLASSIC_BUY100_P4
                continue
        crow = retarget_buy_row(
            replace(cl_cfg, baked={"buy10": EASY_BUY_CLASSIC, "buy100": {}}, prefer_exact_baked=False),
            k,
            "buy100",
        )
        cl_chart[k] = to_json_row(crow, cost)
    # Ensure pick4 diverged
    if cl_chart[4] == EASY_BUY_CLASSIC[4]:
        # nudge via retarget with slightly lower top using temporary ladder override
        tmp = replace(
            cl_cfg,
            json_max_ladder_buy100={**{kk: EASY_BUY_CLASSIC_BUY100[kk][-1] for kk in EASY_BUY_CLASSIC_BUY100}, 4: 16.0},
            baked={"buy10": EASY_BUY_CLASSIC, "buy100": {}},
            prefer_exact_baked=False,
        )
        crow = retarget_buy_row(tmp, 4, "buy100")
        cl_chart[4] = to_json_row(crow, cost)
    show("classic_buy100", "classic", "buy100", cl_chart)
    assert cl_chart[4] != EASY_BUY_CLASSIC[4], "classic pick4 must diverge"
    assert cl_chart[10][-1] == 450.0, cl_chart[10]

    # --- medium ---
    med_chart, med_lad = try_ladders(MEDIUM_BUY_CONFIG, "medium", MED_LADDER_100, MED_LADDER_100_FALLBACKS)
    # Force pick4 body ≠ buy10 even if tops match
    if med_chart[4] == EASY_BUY_MEDIUM[4]:
        for top in (14.0, 15.0, 13.0, 11.0, 10.0):
            try:
                tmp_lad = dict(med_lad)
                tmp_lad[4] = top
                row = to_json_row(retarget_buy_row(replace(
                    MEDIUM_BUY_CONFIG,
                    json_max_ladder_buy100=tmp_lad,
                    baked={"buy10": {}, "buy100": {}},
                    prefer_exact_baked=False,
                ), 4, "buy100"), 100.0)
                if row != EASY_BUY_MEDIUM[4]:
                    med_chart[4] = row
                    med_lad = tmp_lad
                    break
            except Exception as e:
                print("med p4 nudge fail", top, e)
    show("medium_buy100", "medium", "buy100", med_chart)
    assert med_chart[4] != EASY_BUY_MEDIUM[4]
    if med_chart[10][-1] != 450.0:
        print("WARNING: medium pick10 top is", med_chart[10][-1], "not 450 — best legal under RTP")

    # --- high ---
    hi_chart, hi_lad = try_ladders(HIGH_BUY_CONFIG, "high", HI_LADDER_100, HI_LADDER_100_FALLBACKS)
    if hi_chart[4] == EASY_BUY_HIGH[4]:
        for top in (25.0, 24.0, 20.0, 18.0):
            try:
                tmp_lad = dict(hi_lad)
                tmp_lad[4] = top
                row = to_json_row(retarget_buy_row(replace(
                    HIGH_BUY_CONFIG,
                    json_max_ladder_buy100=tmp_lad,
                    baked={"buy10": {}, "buy100": {}},
                    prefer_exact_baked=False,
                ), 4, "buy100"), 100.0)
                if row != EASY_BUY_HIGH[4]:
                    hi_chart[4] = row
                    hi_lad = tmp_lad
                    break
            except Exception as e:
                print("high p4 nudge fail", top, e)
    show("high_buy100", "high", "buy100", hi_chart)
    assert hi_chart[4] != EASY_BUY_HIGH[4]
    assert med_chart != hi_chart
    if hi_chart[10][-1] != 450.0:
        print("WARNING: high pick10 top is", hi_chart[10][-1], "not 450 — best legal under RTP")

    # --- low: separate buy100 bake with mid redistribution; retarget if seed illegal ---
    low_cfg = replace(
        LOW_BUY_CONFIG,
        baked={"buy10": EASY_BUY_LOW, "buy100": LOW_BUY100_SEED},
        prefer_exact_baked=True,
    )
    low_chart = {}
    for k in range(2, 11):
        seed = LOW_BUY100_SEED[k]
        crow = [m / 100.0 for m in seed]
        mask = zero_mask_for(low_cfg, k, "buy100")
        if legal(low_cfg, k, mask, crow, crow[k], 100.0, "buy100"):
            low_chart[k] = seed
        else:
            crow = retarget_buy_row(
                replace(low_cfg, baked={"buy10": EASY_BUY_LOW, "buy100": {}}, prefer_exact_baked=False),
                k,
                "buy100",
            )
            low_chart[k] = to_json_row(crow, 100.0)
            # if still identical to buy10, perturb via small top change not available — leave solver body
            if low_chart[k] == EASY_BUY_LOW[k]:
                print(f"NOTE: low pick{k} still matches buy10 after retarget; accepting solver body")
    # Ensure every row diverges; if not, scale mid cells slightly and re-legalize via retarget empty
    for k in range(2, 11):
        if low_chart[k] == EASY_BUY_LOW[k]:
            # hand-nudge: transfer 0.1 from early pay to later mid if possible
            row = list(low_chart[k])
            paying = [i for i, m in enumerate(row) if m > 0 and i < k]
            if len(paying) >= 2 and row[paying[0]] >= 0.2:
                row[paying[0]] = round(row[paying[0]] - 0.1, 1)
                row[paying[1]] = round(row[paying[1]] + 0.1, 1)
                crow = [m / 100.0 for m in row]
                if legal(low_cfg, k, zero_mask_for(low_cfg, k, "buy100"), crow, crow[k], 100.0, "buy100"):
                    low_chart[k] = row
    show("low_buy100", "low", "buy100", low_chart)
    for k in range(2, 11):
        assert low_chart[k] != EASY_BUY_LOW[k], f"low pick{k} still == buy10"

    # --- write easy_buy_*.py ---
    # classic
    cl_path = GAME / "easy_buy_classic.py"
    patch_file(cl_path, {
        "EASY_BUY_CLASSIC_BUY100": format_dict_int_list("EASY_BUY_CLASSIC_BUY100", cl_chart),
    })

    # medium
    med_path = GAME / "easy_buy_medium.py"
    med_text = med_path.read_text()
    med_text = replace_assignment(med_text, "JSON_MAX_LADDER_BUY100", format_ladder("JSON_MAX_LADDER_BUY100", med_lad))
    med_text = replace_assignment(med_text, "EASY_BUY_MEDIUM_BUY100", format_dict_int_list("EASY_BUY_MEDIUM_BUY100", med_chart))
    # update docstring pin note
    med_text = med_text.replace(
        "buy100 JSON ≤ 450, but deep buy100 tops sit well under that pin",
        "buy100 JSON ≤ 450; deep buy100 tops use the full Max Payout pin",
    )
    med_path.write_text(med_text)
    print("patched easy_buy_medium.py")

    # high
    hi_path = GAME / "easy_buy_high.py"
    hi_text = hi_path.read_text()
    hi_text = replace_assignment(hi_text, "JSON_MAX_LADDER_BUY100", format_ladder("JSON_MAX_LADDER_BUY100", hi_lad))
    hi_text = replace_assignment(hi_text, "EASY_BUY_HIGH_BUY100", format_dict_int_list("EASY_BUY_HIGH_BUY100", hi_chart))
    hi_text = hi_text.replace(
        "buy100 deep tops sit under\nthe 450 pin on a separate ladder",
        "buy100 deep tops use the full 450 Max Payout pin on a separate ladder",
    )
    hi_path.write_text(hi_text)
    print("patched easy_buy_high.py")

    # low: introduce EASY_BUY_LOW_BUY100 and wire config
    low_path = GAME / "easy_buy_low.py"
    low_text = low_path.read_text()
    if "EASY_BUY_LOW_BUY100" not in low_text:
        # insert after EASY_BUY_LOW block
        block = format_dict_int_list("EASY_BUY_LOW_BUY100", low_chart)
        low_text = replace_assignment(low_text, "EASY_BUY_LOW", format_dict_int_list("EASY_BUY_LOW", EASY_BUY_LOW))
        # re-read after — simpler: splice after EASY_BUY_LOW closing
        m = re.search(r"^EASY_BUY_LOW: dict\[int, list\[float\]\] = \{.*?\n\}", low_text, re.M | re.S)
        if not m:
            raise RuntimeError("EASY_BUY_LOW block missing")
        insert = m.group(0) + "\n\n#: buy100 mid-redistributed chart (same tops; bodies ≠ buy10).\n" + block
        low_text = low_text[: m.start()] + insert + low_text[m.end() :]
        low_text = low_text.replace(
            'baked={"buy10": EASY_BUY_LOW, "buy100": EASY_BUY_LOW},',
            'baked={"buy10": EASY_BUY_LOW, "buy100": EASY_BUY_LOW_BUY100},',
        )
        low_text = low_text.replace(
            '"EASY_BUY_LOW",',
            '"EASY_BUY_LOW",\n    "EASY_BUY_LOW_BUY100",',
        )
        # update comment about sharing
        low_text = low_text.replace(
            "#: Shipped Buy `low` chart (picks 2–10), JSON / base-bet units. Shared by\n"
            "#: buy10 and buy100: BUY_LUMEN_BOOST equals chip cost, so one advertised\n"
            "#: ladder settles both chips at the same per-debit RTP.",
            "#: Shipped Buy `low` chart for buy10 (picks 2–10). buy100 uses a separate\n"
            "#: mid-redistributed body (EASY_BUY_LOW_BUY100) so the JSON strip is not dominated.",
        )
        # fix summary/chart references for buy100
        low_text = low_text.replace(
            "chart = EASY_BUY_LOW",
            'chart = EASY_BUY_LOW if buy == "buy10" else EASY_BUY_LOW_BUY100',
        )
        # validation loop may assume shared — update if present
        low_text = low_text.replace(
            "chart = EASY_BUY_LOW\n        for k, row in sorted(chart.items()):",
            'chart = EASY_BUY_LOW if buy == "buy10" else EASY_BUY_LOW_BUY100\n        for k, row in sorted(chart.items()):',
        )
    else:
        low_text = replace_assignment(low_text, "EASY_BUY_LOW_BUY100", format_dict_int_list("EASY_BUY_LOW_BUY100", low_chart))
    low_path.write_text(low_text)
    print("patched easy_buy_low.py")

    # --- patch paytables via solve_paytables ---
    py = GAME.parents[1] / "env" / "bin" / "python"
    if not py.exists():
        py = pathlib.Path(sys.executable)
    cmd = [
        str(py),
        "-c",
        "import solve_paytables as s; s.patch_buy_low(); s.patch_buy_classic(); s.patch_buy_medium(); s.patch_buy_high()",
    ]
    print("running", cmd)
    subprocess.check_call(cmd, cwd=str(GAME))

    after = json.loads(paytables_path.read_text())
    print("\n=== AFTER pick4 / pick10 + howto ===")
    for risk in ("classic", "low", "medium", "high"):
        for k in ("4", "10"):
            r10 = after["buy10"][risk][k]
            r100 = after["buy100"][risk][k]
            diverge = r10 != r100
            how10 = 2 * r10[-1]  # vs debit with Pulse, boost==cost
            how100 = 2 * r100[-1]
            print(f"  {risk} pick{k}: buy10={r10} how≈{how10:.0f}")
            print(f"           buy100={r100} how≈{how100:.0f} diverge={diverge}")
            if k == "4":
                assert diverge, f"{risk} pick4 buy100 still == buy10"

    # leave buy10 intact check
    for risk in ("classic", "low", "medium", "high"):
        assert after["buy10"][risk] == before["buy10"][risk], f"buy10 {risk} changed!"

    # regen books
    print("\n=== run_buy100_all.py ===")
    subprocess.check_call([str(py), "run_buy100_all.py"], cwd=str(GAME))

    # library export if present
    export = GAME / "export_luts.py"
    if export.exists():
        print("=== export_luts.py ===")
        try:
            subprocess.check_call([str(py), "export_luts.py"], cwd=str(GAME))
        except subprocess.CalledProcessError as e:
            print("export_luts failed (non-fatal if library already updated by run):", e)

    print("\nMAX_PAYOUT decision: KEEP buy100 MAX_PAYOUT_ABS=90_000 (3-Star). JSON pin ≤450.")
    print("vs-debit How-to buy100 remains < buy10 on deep picks by rating design (900 vs 4000/4500).")
    print("DONE")


if __name__ == "__main__":
    main()
