"""Regenerate Earn + buy pick_1 books/LUTs after the per-risk Pulse chance."""

from game_config import GameConfig
from gamestate import GameState
from keno_pick_one import (
    BUY_SUFFIXES,
    book_count_for_picks,
    parse_mode_name,
    paying_from_table,
)
from run import write_exact_lookup_tables, write_publish_index
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)
    num_sim_args: dict[str, int] = {}
    for risk in ("classic", "low", "medium", "high"):
        paying = paying_from_table(config.keno_earn_paytable[risk][1])
        num_sim_args[f"{risk}_pick_1_earn"] = book_count_for_picks(1, paying=paying)
        for buy in BUY_SUFFIXES:
            num_sim_args[f"{risk}_pick_1_{buy}"] = book_count_for_picks(
                1, bought=True, placed=False
            )
    create_books(gamestate, config, num_sim_args, 1000, 1, True, False)
    write_exact_lookup_tables(gamestate)
    generate_configs(gamestate)
    write_publish_index(gamestate)
    for name in num_sim_args:
        risk, k, earn, buy = parse_mode_name(name)
        print(f"{name:26s} rtp={gamestate.mode_rtp(risk, k, earn, buy):.4f}")
