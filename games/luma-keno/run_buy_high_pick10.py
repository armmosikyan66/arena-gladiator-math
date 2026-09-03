"""Regenerate Buy high pick 10 books/LUTs (JSON top 5000 buy10 / 500 buy100).

2026-09-03 headline parity: both chips settle 100,000x the base bet at
`high` pick 10 (5000 x 10 x 2 / 500 x 100 x 2), matching Off/Earn.
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

BUY = ("buy10", "buy100")

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)
    num_sim_args = {}
    for buy in BUY:
        paying = paying_from_table(config.keno_buy_paytable[buy]["high"][10])
        name = f"high_pick_10_{buy}"
        num_sim_args[name] = book_count_for_picks(
            10, paying=paying, bought=True, placed=lumen_placed_on_pick(buy, 10)
        )
    create_books(gamestate, config, num_sim_args, 1000, 1, True, False)
    write_exact_lookup_tables(gamestate)
    generate_configs(gamestate)
    write_publish_index(gamestate)
    for name in sorted(num_sim_args):
        risk, k, earn, buy = parse_mode_name(name)
        print(
            f"{name:26s} rtp={gamestate.mode_rtp(risk, k, earn, buy):.4f} "
            f"books={num_sim_args[name]}"
        )
