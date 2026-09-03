"""Regenerate all Buy low modes: low_pick_{1..10}_buy10 and buy100."""

from game_config import GameConfig
from gamestate import GameState
from keno_pick_one import (
    BUY_SUFFIXES,
    book_count_for_picks,
    lumen_placed_on_pick,
    parse_mode_name,
    paying_from_table,
)
from run import write_exact_lookup_tables, write_publish_index
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)
    num_sim_args = {}
    for buy in BUY_SUFFIXES:
        for k in range(1, 11):
            paying = paying_from_table(config.keno_buy_paytable[buy]["low"][k])
            name = f"low_pick_{k}_{buy}"
            num_sim_args[name] = book_count_for_picks(
                k, paying=paying, bought=True, placed=lumen_placed_on_pick(buy, k)
            )
    print("modes:", len(num_sim_args), sorted(num_sim_args))
    create_books(gamestate, config, num_sim_args, 1000, 1, True, False)
    write_exact_lookup_tables(gamestate)
    generate_configs(gamestate)
    write_publish_index(gamestate)
    for name in sorted(num_sim_args):
        risk, k, earn, buy = parse_mode_name(name)
        print(f"{name:26s} rtp={gamestate.mode_rtp(risk, k, earn, buy):.4f} books={num_sim_args[name]}")
