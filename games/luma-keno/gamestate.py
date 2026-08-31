"""Single-shot keno round."""

from keno_pick_one import (
    PULSE_BOOST,
    REASON_TO_EVENT,
    lumen_boost_applied,
    lumen_boost_for,
    lumen_placed_on_pick,
    pulse_boost_applied,
)
from game_events import keno_catch_event, keno_start_event, keno_win_events
from game_override import GameStateOverride


class GameState(GameStateOverride):
    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            risk, k, earn, buy = self.mode_parts()
            spin = self.spin_from_criteria()
            if earn:
                base = self.pay_for(risk, k, spin.total_hits, True, buy)
                after_lumen = self.settle_pay(
                    risk, k, spin.total_hits, spin.lumen_hit, True, False, buy
                )
                pay = self.settle_pay(
                    risk, k, spin.total_hits, spin.lumen_hit, True, spin.pulse, buy
                )
                keno_start_event(
                    self,
                    risk,
                    k,
                    self.pay_row_for(risk, k, True, buy),
                    lumen_boost_for(risk, buy),
                    True,
                    PULSE_BOOST[risk],
                    lumen_placed_on_pick(buy, k),
                )
                keno_catch_event(
                    self,
                    spin.main_hits,
                    spin.total_hits,
                    pay,
                    spin.lumen_hit,
                    spin.extras,
                    REASON_TO_EVENT[spin.extra_reason],
                    spin.extra_hits,
                    lumen_boost_applied(base, spin.lumen_hit, risk, buy),
                    pulse_boost_applied(after_lumen, spin.pulse, risk),
                )
            else:
                hits = spin.main_hits
                pay = self.off_pay_for(risk, k, spin)
                keno_start_event(
                    self, risk, k, self.pay_row_for(risk, k, False), 1.0, False, 1.0
                )
                keno_catch_event(
                    self,
                    hits,
                    hits,
                    pay,
                    False,
                    False,
                    None,
                    0,
                    1.0,
                    1.0,
                )
            self.win_manager.update_spinwin(pay)
            self.win_manager.update_gametype_wins(self.gametype)
            keno_win_events(self)
            self.check_repeat()
        self.imprint_wins()

    def run_freespin(self):
        return
