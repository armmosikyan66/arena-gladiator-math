"""Keno math helpers."""

from math import comb

from keno_pick_one import (
    parse_mode_name,
    parse_spin_criteria,
    paying_from_table,
    settle_pay as settle_amount,
    spin_outcomes,
    spin_weight,
    weight_scale,
)
from src.executables.executables import Executables


class GameCalculations(Executables):
    def hit_weight(self, k: int, h: int) -> int:
        drawn = self.config.keno_drawn
        rest = self.config.keno_pool - drawn
        if h < 0 or h > k or (k - h) > rest or h > drawn:
            return 0
        return comb(drawn, h) * comb(rest, k - h)

    def mode_parts(self) -> tuple[str, int, bool]:
        """Split mode name into (risk, k, earn)."""
        return parse_mode_name(self.get_current_betmode().get_name())

    def picks_for_mode(self) -> int:
        return self.mode_parts()[1]

    def hits_from_criteria(self) -> int:
        return self.spin_from_criteria().main_hits

    def lumen_hit_from_criteria(self) -> bool:
        return self.spin_from_criteria().lumen_hit

    def spin_from_criteria(self):
        return parse_spin_criteria(str(self.criteria))

    def pay_row_for(self, risk: str, k: int, earn: bool) -> list[float]:
        return [self.pay_for(risk, k, h, earn) for h in range(k + 1)]

    def pay_for(self, risk: str, k: int, h: int, earn: bool) -> float:
        tables = self.config.keno_earn_paytable if earn else self.config.keno_paytable
        table = tables[risk][k]
        if 0 <= h < len(table):
            return round(float(table[h] or 0), 1)
        return 0.0

    def settle_pay(
        self,
        risk: str,
        k: int,
        hits: int,
        lumen_hit: bool,
        earn: bool,
        pulse: bool = False,
    ) -> float:
        base = self.pay_for(risk, k, hits, earn)
        if earn:
            return settle_amount(base, lumen_hit, pulse, risk)
        return base

    def mode_rtp(self, risk: str, k: int, earn: bool) -> float:
        if not earn:
            total = comb(self.config.keno_pool, k)
            return sum(
                self.hit_weight(k, h) * self.pay_for(risk, k, h, False)
                for h in range(k + 1)
            ) / total
        paying = paying_from_table(self.pay_row_for(risk, k, True))
        total = comb(self.config.keno_pool, k) * self.config.keno_drawn * weight_scale()
        return sum(
            spin_weight(k, spin, risk, paying=paying)
            * self.settle_pay(risk, k, spin.total_hits, spin.lumen_hit, True, spin.pulse)
            for spin in spin_outcomes(k, self.config.keno_drawn, paying)
        ) / total
