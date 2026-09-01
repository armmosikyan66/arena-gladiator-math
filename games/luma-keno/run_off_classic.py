"""Regenerate Off classic books/LUTs (geometric ladder, picks 1–10)."""

from game_config import GameConfig
from gamestate import GameState
from keno_pick_one import off_outcomes, parse_mode_name
from run import write_exact_lookup_tables, write_publish_index
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)
    num_sim_args = {
        f"classic_pick_{k}": len(off_outcomes(k, "classic")) for k in range(1, 11)
    }
    create_books(gamestate, config, num_sim_args, 1000, 1, True, False)
    write_exact_lookup_tables(gamestate)
    generate_configs(gamestate)
    write_publish_index(gamestate)
    for name in num_sim_args:
        risk, k, earn, buy = parse_mode_name(name)
        print(f"{name:20s} rtp={gamestate.mode_rtp(risk, k, earn, buy):.4f}")
