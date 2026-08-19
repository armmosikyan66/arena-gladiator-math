"""Tower overrides of universal state.py functions."""

import random

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Overrides for game specific state behaviour."""

    def reset_book(self):
        """Reset game specific properties."""
        super().reset_book()
        # Instance RNG, deterministically seeded per simulation in run_spin.
        self.rng = random.Random(self.sim + 1)
        self.tower_mines = []
        self.tower_coefficient = 1.0
        self.tower_row_bonuses = {}
        self.tower_session = None

    def assign_special_sym_function(self):
        pass

    def evaluate_finalwin(self) -> None:
        """Set book payout WITHOUT emitting ``finalWin``.

        Tower is multi-step: the round must stay ``active`` on Stake until
        the front-end calls ``/wallet/end-round``.  The ``finalWin`` event
        signals "round complete" to the RGS, which causes ``active: false``.
        We still call ``update_final_win()`` so ``payoutMultiplier`` is set
        on the book root for LUT verification.
        """
        self.update_final_win()
