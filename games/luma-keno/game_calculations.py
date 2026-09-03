"""Keno math helpers."""

from math import comb

from keno_pick_one import (
    BUY_SUFFIXES,
    lumen_placed_on_pick,
    off_outcomes,
    off_pay,
    off_weight,
    parse_mode_name,
    parse_spin_criteria,
    paying_from_table,
    settle_pay as settle_amount,
    spin_outcomes,
    spin_weight,
    weight_total,
)
from src.executables.executables import Executables


class GameCalculations(Executables):
    def hit_weight(self, k: int, h: int) -> int:
        drawn = self.config.keno_drawn
        rest = self.config.keno_pool - drawn
        if h < 0 or h > k or (k - h) > rest or h > drawn:
            return 0
        return comb(drawn, h) * comb(rest, k - h)

    def mode_parts(self) -> tuple[str, int, bool, str | None]:
        """Split mode name into (risk, k, earn, buy)."""
        return parse_mode_name(self.get_current_betmode().get_name())

    def picks_for_mode(self) -> int:
        return self.mode_parts()[1]

    def hits_from_criteria(self) -> int:
        return self.spin_from_criteria().main_hits

    def lumen_hit_from_criteria(self) -> bool:
        return self.spin_from_criteria().lumen_hit

    def spin_from_criteria(self):
        return parse_spin_criteria(str(self.criteria))

    def pay_row_for(
        self, risk: str, k: int, earn: bool, buy: str | None = None
    ) -> list[float]:
        return [self.pay_for(risk, k, h, earn, buy) for h in range(k + 1)]

    def off_pay_for(self, risk: str, k: int, spin) -> float:
        """Off payout for a book. Only differs from `pay_for` on pick_1's bonus
        miss tier, which pays above the row indexed by hits."""
        return off_pay(spin, self.config.keno_paytable[risk][k])

    def pay_for(
        self, risk: str, k: int, h: int, earn: bool, buy: str | None = None
    ) -> float:
        if buy is not None:
            table = self.config.keno_buy_paytable[buy][risk][k]
        else:
            tables = (
                self.config.keno_earn_paytable if earn else self.config.keno_paytable
            )
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
        buy: str | None = None,
    ) -> float:
        base = self.pay_for(risk, k, hits, earn, buy)
        if earn:
            return settle_amount(base, lumen_hit, pulse, risk, buy)
        return base

    def mode_rtp(self, risk: str, k: int, earn: bool, buy: str | None = None) -> float:
        if not earn:
            total = comb(self.config.keno_pool, k)
            return sum(
                off_weight(k, spin, risk) * self.off_pay_for(risk, k, spin)
                for spin in off_outcomes(k, risk)
            ) / total
        bought = buy is not None
        placed = lumen_placed_on_pick(buy, k)
        paying = paying_from_table(self.pay_row_for(risk, k, True, buy))
        total = weight_total(k, placed=placed)
        # Buy rounds are priced per cost, so the return has to be divided by what
        # the round charged before it can be compared with a 1x mode.
        cost = BUY_SUFFIXES[buy] if bought else 1.0
        return sum(
            spin_weight(
                k, spin, risk, paying=paying, bought=bought, placed=placed, buy=buy
            )
            * self.settle_pay(
                risk, k, spin.total_hits, spin.lumen_hit, True, spin.pulse, buy
            )
            for spin in spin_outcomes(
                k, self.config.keno_drawn, paying, bought, placed
            )
        ) / (total * cost)
