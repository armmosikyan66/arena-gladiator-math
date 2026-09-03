"""Regenerate Buy low picks 3/6/9/10 books/LUTs (restairs + climb gate).

The book count must enumerate the *buy* outcome space: both extras forced
open and the Lumen mark guaranteed on one pick. Building it on the Earn
lattice (the default) settles buy payouts over earn criteria and the LUT
RTP lands anywhere but the window.
"""

from game_config import GameConfig
from gamestate import GameState
from keno_pick_one import (
    book_count_for_picks,
    lumen_placed_on_pick,
    parse_mode_name,
    paying_from_table,
)
from run import write_exact_lookup_tables, write_publish_index
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

PICKS = (3, 6, 9, 10)
BUY = "buy10"

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)
    num_sim_args = {}
    for k in PICKS:
        paying = paying_from_table(config.keno_buy_paytable[BUY]["low"][k])
        name = f"low_pick_{k}_{BUY}"
        num_sim_args[name] = book_count_for_picks(
            k, paying=paying, bought=True, placed=lumen_placed_on_pick(BUY, k)
        )
    create_books(gamestate, config, num_sim_args, 1000, 1, True, False)
    write_exact_lookup_tables(gamestate)
    generate_configs(gamestate)
    write_publish_index(gamestate)
    for name in num_sim_args:
        risk, k, earn, buy = parse_mode_name(name)
        print(f"{name:26s} rtp={gamestate.mode_rtp(risk, k, earn, buy):.4f}")
