"""Luma Keno configuration. Pool 40 / drawn 10, picks 1-10, 4 risk modes.

Paytables are solved analytically (solve_paytables.py) against the local
3-Star verifier gates and loaded from paytables.json. All 40 modes share one
RTP target; risk only reshapes variance.
"""

import json
import os

from src.config.betmode import BetMode
from src.config.config import Config
from src.config.distributions import Distribution

_RISKS = ("classic", "low", "medium", "high")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "paytables.json"), encoding="UTF-8") as _fh:
    _PAYTABLE_DOC = json.load(_fh)


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
        # {risk: {k: [multiplier per hit count]}}
        self.keno_paytable = {
            risk: {int(k): row for k, row in tables.items()}
            for risk, tables in _PAYTABLE_DOC["risks"].items()
        }
        max_pay = max(
            row[-1] for tables in self.keno_paytable.values() for row in tables.values()
        )
        self.wincap = max_pay
        # All modes converge on the same realized RTP (0.9485-0.9515 after
        # 0.1x rounding); the config-level RTP is the shared target. 0.95 is
        # the pick_1 lattice point (3.8x on P=0.25) — see solve_paytables.py.
        self.rtp = float(_PAYTABLE_DOC["rtp_target"])
        self.bet_modes = [
            self._pick_mode(risk, k) for risk in self.keno_risks for k in self.keno_picks
        ]
        self.opt_params = {}

    def _pick_mode(self, risk: str, k: int) -> BetMode:
        n = k + 1
        return BetMode(
            name=f"{risk}_pick_{k}",
            cost=1.0,
            rtp=self.rtp,
            max_win=max(self.keno_paytable[risk][k]),
            auto_close_disabled=False,
            is_feature=True,
            is_buybonus=False,
            distributions=[
                Distribution(
                    criteria=f"hits_{h}",
                    quota=1.0 / n,
                    win_criteria=None,
                    conditions={"force_wincap": False, "force_freegame": False},
                    required_distribution_conditions=[],
                )
                for h in range(n)
            ],
        )
