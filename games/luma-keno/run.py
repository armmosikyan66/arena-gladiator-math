"""Luma Keno pipeline. 40 modes (4 risks x 10 pick sizes), exact LUT weights.

The Rust optimizer is skipped on purpose: LUT weights are the true
hypergeometric counts C(drawn, h) * C(pool - drawn, k - h) and payouts are the
solved paytable values. Optimizing would destroy the certified odds.
"""

from math import comb
import json
import os

from game_config import GameConfig
from gamestate import GameState
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs


def parse_mode(name: str) -> tuple[str, int]:
    risk, pick = name.rsplit("_pick_", 1)
    return risk, int(pick)


def write_exact_lookup_tables(gamestate: GameState) -> None:
    """Replace sim counts with hypergeometric weights. Skip the Rust optimizer."""
    drawn = gamestate.config.keno_drawn
    rest = gamestate.config.keno_pool - drawn
    for mode in gamestate.config.bet_modes:
        name = mode.get_name()
        _, k = parse_mode(name)
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
                hits = int(criteria.rsplit("_", 1)[-1])
                weight = comb(drawn, hits) * comb(rest, k - hits)
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
    print(f"\n{'mode':>16} {'RTP':>8}   top prize")
    for mode in gamestate.config.bet_modes:
        risk, k = parse_mode(mode.get_name())
        rtp = gamestate.mode_rtp(risk, k)
        print(f"{mode.get_name():>16} {rtp:8.4f}   {gamestate.pay_for(risk, k, k):>9.1f}x")


if __name__ == "__main__":
    num_threads = 1
    batching_size = 50
    compression = True
    profiling = False

    num_sim_args = {
        f"{risk}_pick_{k}": k + 1
        for risk in ("classic", "low", "medium", "high")
        for k in range(1, 11)
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "upload_data": False,
    }

    config = GameConfig()
    gamestate = GameState(config)

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
