#!/usr/bin/env python3
"""Exact keno RTP and 3-Star-ish stats from a paytable JSON.

Usage:
  python3 rtp.py paytable.json
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def hit_weight(k: int, h: int, drawn: int, pool: int) -> int:
    rest = pool - drawn
    if h < 0 or h > k or (k - h) > rest or h > drawn:
        return 0
    return math.comb(drawn, h) * math.comb(rest, k - h)


def moments_and_tails(outcomes: list[tuple[int, float]], total_w: int, bet_cost: float = 1.0):
    """outcomes: (weight, multiplier) for h = 0..k."""
    rtp = sum(w * m for w, m in outcomes) / total_w / bet_cost
    mean = sum(w * m for w, m in outcomes) / total_w
    var = sum(w * (m - mean) ** 2 for w, m in outcomes) / total_w
    std = math.sqrt(var)

    def p_ge(threshold: float) -> float:
        return sum(w for w, m in outcomes if m >= threshold) / total_w

    def etl(threshold: float) -> float:
        return sum(w * m for w, m in outcomes if m >= threshold) / total_w

    # CVaR: E[m | m in worst 0.1% tail] / bet_cost (discrete, from the right).
    ranked = sorted(outcomes, key=lambda t: t[1], reverse=True)
    tail_mass = 0.001 * total_w
    acc_w = 0.0
    acc_wm = 0.0
    for w, m in ranked:
        take = min(w, tail_mass - acc_w)
        if take <= 0:
            break
        acc_w += take
        acc_wm += take * m
        if acc_w >= tail_mass:
            break
    cvar = (acc_wm / acc_w / bet_cost) if acc_w else 0.0

    return {
        "rtp": rtp,
        "std": std,
        "p5k": p_ge(5000),
        "p10k": p_ge(10000),
        "etl40": etl(40 * bet_cost),
        "etl10k": etl(10000),
        "cvar": cvar,
        "max_m": max(m for _, m in outcomes),
    }


def analyze(payload: dict) -> None:
    pool = int(payload.get("pool", 80))
    drawn = int(payload.get("drawn", 20))
    target = payload.get("rtp_target")
    picks = payload["picks"]

    print(f"pool={pool} drawn={drawn} rtp_target={target}")
    print(f"{'k':>3} {'RTP':>10} {'std':>10} {'max':>10} {'P5K':>10} {'P10K':>10} {'CVaR':>10} {'ETL40':>10}")

    rtps = []
    for k_s, table in sorted(picks.items(), key=lambda kv: int(kv[0])):
        k = int(k_s)
        rows = []
        for h in range(k + 1):
            m = float(table.get(str(h), table.get(h, 0)) or 0)
            rows.append((hit_weight(k, h, drawn, pool), m))
        total = math.comb(pool, k)
        stats = moments_and_tails(rows, total)
        rtps.append(stats["rtp"])
        print(
            f"{k:3d} {stats['rtp']:10.6f} {stats['std']:10.4f} {stats['max_m']:10.1f} "
            f"{stats['p5k']:10.6f} {stats['p10k']:10.6f} {stats['cvar']:10.2f} {stats['etl40']:10.4f}"
        )
        if target is not None and abs(stats["rtp"] - float(target)) > 0.002:
            print(f"    WARN RTP off target by {stats['rtp'] - float(target):+.4f}")

    if len(rtps) > 1:
        gap = max(rtps) - min(rtps)
        print(f"mode RTP spread={gap:.4f} (verifier warns if > 0.05)")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    payload = json.loads(path.read_text())
    analyze(payload)


if __name__ == "__main__":
    main()
