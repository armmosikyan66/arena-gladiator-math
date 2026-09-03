"""Luma Keno pipeline. 80 modes: Off table-only + Earn (Lumen/extras).

The Rust optimizer is skipped on purpose: Off LUT weights are exact
hypergeometric hit counts. Earn weights also split Lumen slots, extra-open
chances, and extra-pair counts. Payouts are the mode table, × Lumen on Earn.
"""

import json
import os

from game_config import GameConfig
from gamestate import GameState
from keno_pick_one import (
    BUY_SUFFIXES,
    book_count_for_picks,
    lumen_placed_on_pick,
    off_outcomes,
    off_weight,
    parse_mode_name,
    parse_spin_criteria,
    paying_from_table,
    spin_weight,
)
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs


def write_exact_lookup_tables(gamestate: GameState) -> None:
    """Replace sim counts with exact keno weights. Skip the Rust optimizer."""
    for mode in gamestate.config.bet_modes:
        name = mode.get_name()
        risk, k, earn, buy = parse_mode_name(name)
        base_lut = gamestate.output_files.get_final_lookup_name(name)
        opt_lut = gamestate.output_files.get_optimized_lookup_name(name)
        segmented = gamestate.output_files.get_final_segmented_name(name)

        payouts = {}
        with open(base_lut, encoding="UTF-8") as handle:
            for line in handle:
                sim_id, _, payout = line.strip().split(",")
                payouts[sim_id] = payout

        rows = []
        with open(segmented, encoding="UTF-8") as handle:
            for line in handle:
                sim_id, criteria, *_ = line.strip().split(",")
                spin = parse_spin_criteria(criteria)
                if earn:
                    table = (
                        gamestate.config.keno_buy_paytable[buy][risk][k]
                        if buy
                        else gamestate.config.keno_earn_paytable[risk][k]
                    )
                    paying = paying_from_table(table)
                    weight = spin_weight(
                        k,
                        spin,
                        risk,
                        paying=paying,
                        bought=buy is not None,
                        placed=lumen_placed_on_pick(buy, k),
                        buy=buy,
                    )
                else:
                    weight = off_weight(k, spin, risk)
                rows.append(f"{sim_id},{weight},{payouts[sim_id]}\n")

        text = "".join(rows)
        for path in (base_lut, opt_lut):
            with open(path, "w", encoding="UTF-8") as handle:
                handle.write(text)


def write_publish_index(gamestate: GameState) -> str:
    """ACP only needs this manifest plus the books/LUT files it names."""
    modes = []
    for mode in gamestate.config.bet_modes:
        name = mode.get_name()
        modes.append(
            {
                "name": name,
                "cost": float(mode.get_cost()),
                "events": f"books_{name}.jsonl.zst",
                "weights": f"lookUpTable_{name}_0.csv",
            }
        )
    path = os.path.join(gamestate.output_files.publish_path, "index.json")
    with open(path, "w", encoding="UTF-8") as handle:
        json.dump({"modes": modes}, handle, indent=4)
    return path


def print_mode_rtp_table(gamestate: GameState) -> None:
    print(f"\n{'mode':>26} {'RTP':>8}   top prize")
    for mode in gamestate.config.bet_modes:
        risk, k, earn, buy = parse_mode_name(mode.get_name())
        rtp = gamestate.mode_rtp(risk, k, earn, buy)
        top = (
            gamestate.settle_pay(risk, k, k, True, earn, True, buy)
            if earn
            else gamestate.pay_for(risk, k, k, False)
        )
        print(f"{mode.get_name():>26} {rtp:8.4f}   {top:>9.1f}x")


if __name__ == "__main__":
    num_threads = 1
    # Must be >= the largest book count. run_multi_process_sims floors
    # `sims_per_thread = int(n / repeats)`, so any mode whose book count is
    # under the batch size runs as one repeat (lossless), while a count that
    # straddles it — 99 books against a batch of 50 — splits into 2 repeats of
    # 49 and silently drops a book. Extra-open Pulse gating made several Earn
    # counts odd (81/89/99), which is what surfaced this. All counts are <= 112.
    batching_size = 1000
    compression = True
    profiling = False

    config = GameConfig()
    gamestate = GameState(config)

    num_sim_args = {}
    for risk in ("classic", "low", "medium", "high"):
        for k in range(1, 11):
            num_sim_args[f"{risk}_pick_{k}"] = len(off_outcomes(k, risk))
            paying = paying_from_table(config.keno_earn_paytable[risk][k])
            num_sim_args[f"{risk}_pick_{k}_earn"] = book_count_for_picks(k, paying=paying)
            for buy in BUY_SUFFIXES:
                buy_paying = paying_from_table(config.keno_buy_paytable[buy][risk][k])
                num_sim_args[f"{risk}_pick_{k}_{buy}"] = book_count_for_picks(
                    k,
                    paying=buy_paying,
                    bought=True,
                    placed=lumen_placed_on_pick(buy, k),
                )

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "upload_data": False,
    }

    if run_conditions["run_sims"] and num_sim_args:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )
        write_exact_lookup_tables(gamestate)
        generate_configs(gamestate)
        write_publish_index(gamestate)
        print_mode_rtp_table(gamestate)

    publish_path = gamestate.output_files.publish_path
    index_path = os.path.join(publish_path, "index.json")
    print(f"{config.game_id}: publish folder is {publish_path}")
    print("index.json exists:", os.path.isfile(index_path))
