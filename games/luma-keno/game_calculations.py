"""Keno math helpers."""

from math import comb

from src.executables.executables import Executables


class GameCalculations(Executables):
    def hit_weight(self, k: int, h: int) -> int:
        drawn = self.config.keno_drawn
        rest = self.config.keno_pool - drawn
        if h < 0 or h > k or (k - h) > rest or h > drawn:
            return 0
        return comb(drawn, h) * comb(rest, k - h)

    def mode_parts(self) -> tuple[str, int]:
        """Split '{risk}_pick_{k}' into (risk, k)."""
        risk, pick = self.get_current_betmode().get_name().rsplit("_pick_", 1)
        return risk, int(pick)

    def picks_for_mode(self) -> int:
        return self.mode_parts()[1]

    def hits_from_criteria(self) -> int:
        return int(str(self.criteria).rsplit("_", 1)[-1])

    def pay_row_for(self, risk: str, k: int) -> list[float]:
        return [self.pay_for(risk, k, h) for h in range(k + 1)]

    def pay_for(self, risk: str, k: int, h: int) -> float:
        table = self.config.keno_paytable[risk][k]
        if 0 <= h < len(table):
            return round(float(table[h] or 0), 1)
        return 0.0

    def mode_rtp(self, risk: str, k: int) -> float:
        total = comb(self.config.keno_pool, k)
        return sum(
            self.hit_weight(k, h) * self.pay_for(risk, k, h) for h in range(k + 1)
        ) / total
