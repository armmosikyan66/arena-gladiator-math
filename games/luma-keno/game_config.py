"""Luma Keno configuration. Pool 40 / drawn 10, picks 1-10, 4 risk modes.

Off modes `{risk}_pick_{k}` are table-only. Earn modes `{risk}_pick_{k}_earn`
price Lumen + extras into a separate 0.950 table. Both share the same
house edge so Cross-Mode RTP stays under 0.50pp.
"""

import json
import os

from keno_pick_one import (
    BUY_SUFFIXES,
    PULSE_BOOST,
    hit_criteria_base,
    hit_criteria_name,
    lumen_boost_for,
    lumen_placed_on_pick,
    mode_name,
    off_outcomes,
    paying_from_table,
    spin_outcomes,
)
from src.config.betmode import BetMode
from src.config.config import Config
from src.config.distributions import Distribution

_RISKS = ("classic", "low", "medium", "high")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "paytables.json"), encoding="UTF-8") as _fh:
    _PAYTABLE_DOC = json.load(_fh)


def _tables(doc_key: str) -> dict[str, dict[int, list[float]]]:
    return {
        risk: {int(k): row for k, row in tables.items()}
        for risk, tables in _PAYTABLE_DOC[doc_key].items()
    }


class GameConfig(Config):
    """Keno identity with unused slot fields left empty."""

    def __init__(self):
        super().__init__()
        self.game_id = "luma-keno"
        self.provider_name = "luma"
        self.provider_number = 1
        self.working_name = "luma_keno"
        self.game_name = "Luma Keno"
        self.win_type = "other"
        self.output_regular_json = False
        self.construct_paths()

        self.num_reels = 0
        self.num_rows = []
        self.paytable = {}
        self.include_padding = False
        self.special_symbols = {"wild": [], "scatter": [], "multiplier": []}
        self.freespin_triggers = {self.basegame_type: {}, self.freegame_type: {}}
        self.anticipation_triggers = {self.basegame_type: 0, self.freegame_type: 0}
        self.reels = {}
        self.padding_reels = {}

        self.keno_pool = _PAYTABLE_DOC["pool"]
        self.keno_drawn = _PAYTABLE_DOC["drawn"]
        self.keno_picks = range(_PAYTABLE_DOC["picks"]["min"], _PAYTABLE_DOC["picks"]["max"] + 1)
        self.keno_risks = _RISKS
        self.keno_paytable = _tables("risks")
        self.keno_earn_paytable = _tables("earn")
        self.keno_buy_paytable = {buy: _tables(buy) for buy in BUY_SUFFIXES}
        off_max = max(max(row) for tables in self.keno_paytable.values() for row in tables.values())
        earn_max = max(
            round(max(row) * lumen_boost_for(risk) * PULSE_BOOST[risk], 1)
            for risk, tables in self.keno_earn_paytable.items()
            for row in tables.values()
        )
        buy_max = max(
            round(max(row) * lumen_boost_for(risk, buy) * PULSE_BOOST[risk], 1)
            for buy, tables in self.keno_buy_paytable.items()
            for risk, rows in tables.items()
            for row in rows.values()
        )
        self.wincap = max(off_max, earn_max, buy_max)
        self.rtp = float(_PAYTABLE_DOC["rtp_target"])
        self.bet_modes = [
            mode
            for risk in self.keno_risks
            for k in self.keno_picks
            for mode in (
                self._off_mode(risk, k),
                self._earn_mode(risk, k),
                *(self._buy_mode(risk, k, buy) for buy in BUY_SUFFIXES),
            )
        ]
        self.opt_params = {}

    def _off_mode(self, risk: str, k: int) -> BetMode:
        outcomes = off_outcomes(k, risk)
        n = len(outcomes)
        return BetMode(
            name=mode_name(risk, k, False),
            cost=1.0,
            rtp=self.rtp,
            max_win=round(max(self.keno_paytable[risk][k]), 1),
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=False,
            distributions=[
                Distribution(
                    criteria=hit_criteria_base(spin.main_hits, spin.miss_bonus),
                    quota=1.0 / n,
                    win_criteria=None,
                    conditions={"force_wincap": False, "force_freegame": False},
                    required_distribution_conditions=[],
                )
                for spin in outcomes
            ],
        )

    def _earn_mode(self, risk: str, k: int) -> BetMode:
        paying = paying_from_table(self.keno_earn_paytable[risk][k])
        outcomes = spin_outcomes(k, self.keno_drawn, paying)
        n = len(outcomes)
        return BetMode(
            name=mode_name(risk, k, True),
            cost=1.0,
            rtp=self.rtp,
            max_win=round(max(self.keno_earn_paytable[risk][k]) * lumen_boost_for(risk) * PULSE_BOOST[risk], 1),
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=False,
            distributions=[
                Distribution(
                    criteria=hit_criteria_name(spin),
                    quota=1.0 / n,
                    win_criteria=None,
                    conditions={"force_wincap": False, "force_freegame": False},
                    required_distribution_conditions=[],
                )
                for spin in outcomes
            ],
        )

    def _buy_mode(self, risk: str, k: int, buy: str) -> BetMode:
        """A buy chip: Earn rules, extras forced open, cost a stake multiple.

        `max_win` stays in base-stake units like the other modes, so it reads as
        the buy table's top row settled through both bonuses. Divided by `cost`
        it is a far smaller multiple than Earn's, which is the point: the player
        has already paid for the shape.
        """
        table = self.keno_buy_paytable[buy][risk][k]
        paying = paying_from_table(table)
        placed = lumen_placed_on_pick(buy, k)
        outcomes = spin_outcomes(k, self.keno_drawn, paying, True, placed)
        n = len(outcomes)
        return BetMode(
            name=mode_name(risk, k, True, buy),
            cost=BUY_SUFFIXES[buy],
            rtp=self.rtp,
            max_win=round(max(table) * lumen_boost_for(risk, buy) * PULSE_BOOST[risk], 1),
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=True,
            distributions=[
                Distribution(
                    criteria=hit_criteria_name(spin),
                    quota=1.0 / n,
                    win_criteria=None,
                    conditions={"force_wincap": False, "force_freegame": False},
                    required_distribution_conditions=[],
                )
                for spin in outcomes
            ],
        )
