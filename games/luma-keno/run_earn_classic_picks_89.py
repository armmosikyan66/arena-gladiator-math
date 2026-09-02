"""Regenerate Earn classic picks 8-9 books/LUTs (750 < 900 < 1000 climb)."""

from game_config import GameConfig
from gamestate import GameState
from keno_pick_one import book_count_for_picks, parse_mode_name, paying_from_table
from run import write_exact_lookup_tables, write_publish_index
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

PICKS = (8, 9)

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)
    num_sim_args = {}
    for k in PICKS:
        paying = paying_from_table(config.keno_earn_paytable["classic"][k])
        name = f"classic_pick_{k}_earn"
        num_sim_args[name] = book_count_for_picks(k, paying=paying)
    create_books(gamestate, config, num_sim_args, 1000, 1, True, False)
    write_exact_lookup_tables(gamestate)
    generate_configs(gamestate)
    write_publish_index(gamestate)
    for name in num_sim_args:
        risk, k, earn, buy = parse_mode_name(name)
        print(f"{name:26s} rtp={gamestate.mode_rtp(risk, k, earn, buy):.4f}")
