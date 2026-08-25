from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    def reset_book(self):
        super().reset_book()

    def assign_special_sym_function(self):
        self.special_symbol_functions = {}

    def check_repeat(self) -> None:
        """Keno hits are forced from criteria; never retry for payout drift."""
        self.repeat_count += 1
        self.check_current_repeat_count()
