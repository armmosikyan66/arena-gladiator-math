"""Single-shot keno round."""

from game_events import keno_catch_event, keno_start_event, keno_win_events
from game_override import GameStateOverride


class GameState(GameStateOverride):
    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            risk, k = self.mode_parts()
            h = self.hits_from_criteria()
            pay = self.pay_for(risk, k, h)
            keno_start_event(self, risk, k, self.pay_row_for(risk, k))
            keno_catch_event(self, h, pay)
            self.win_manager.update_spinwin(pay)
            self.win_manager.update_gametype_wins(self.gametype)
            keno_win_events(self)
            self.check_repeat()
        self.imprint_wins()

    def run_freespin(self):
        return
