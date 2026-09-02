"""Regenerate Earn medium pick_10 books/LUTs (HUD 8<9<10 max ladder)."""

from game_config import GameConfig
from gamestate import GameState
from keno_pick_one import book_count_for_picks, parse_mode_name, paying_from_table
from run import write_exact_lookup_tables, write_publish_index
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)
    paying = paying_from_table(config.keno_earn_paytable["medium"][10])
    name = "medium_pick_10_earn"
    num_sim_args = {name: book_count_for_picks(10, paying=paying)}
    create_books(gamestate, config, num_sim_args, 1000, 1, True, False)
    write_exact_lookup_tables(gamestate)
    generate_configs(gamestate)
    write_publish_index(gamestate)
    risk, k, earn, buy = parse_mode_name(name)
    print(f"{name:26s} rtp={gamestate.mode_rtp(risk, k, earn, buy):.4f}")
