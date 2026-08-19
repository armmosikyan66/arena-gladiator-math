"""Gladiator Tower game configuration.

Climb economy mirrors the BitKong-style tower: per-difficulty row/cols/safe-tile
geometry, fair-odds × depth-house-edge ladders, and bonus rows at 3 / 6 / 9.

Stake modes
-----------
* ``easy`` / ``medium`` / … — **session open** at Start.
  Book root ``payoutMultiplier`` = 100 (1×); UI payout = bet.
  Round stays ``active`` until ``/wallet/end-round``.
  Mine: client closes session then plays ``*_loss`` (no kept refund).

* ``{difficulty}_loss`` / ``{difficulty}_{n}`` — **settle** at cashout/loss
  (depth modes keep bare ladder payouts for backward compat).
* ``{difficulty}_p{payout×100}`` — **bonus-aware settle** (e.g. ``easy_p440``
  pays 4.4× = 2.2 ladder × 2 bonus). Client cashout must use these.

Multipliers: fair odds × house edge per difficulty.
``maxWinning`` only truncates playable height / caps cashout.
"""

from src.config.config import Config
from src.config.distributions import Distribution
from src.config.config import BetMode

from game_calculations import (
    BASE_HOUSE_EDGE,
    DEFAULT_MAX_BET,
    DEFAULT_MAX_PAYOUT,
    DIFFICULTIES,
    bonus_chances_for_difficulty,
    bonuses_for_difficulty,
    build_multipliers,
    build_row_steps,
    enumerate_settle_payouts,
    mines_for,
    session_rtp,
    settle_mode_name,
    win_chance,
)


class GameConfig(Config):
    """Configuration class for the Gladiator Tower game.

    See module docstring for the Stake mode layout (session open + settle).
    """

    def __init__(self):
        super().__init__()
        self.game_id = "gladiator-tower"
        self.provider_name = "gladiator_tower_provider"
        self.provider_number = 0
        self.working_name = "gladiator-tower"
        self.game_name = "Gladiator Tower"
        self.win_type = "other"

        self.house_edge = BASE_HOUSE_EDGE
        self.difficulties = DIFFICULTIES
        self.max_payout = DEFAULT_MAX_PAYOUT
        self.max_bet = DEFAULT_MAX_BET

        self.min_denomination = 1.0  # dollar bets

        self.tower_modes = {}
        self.wincap = 0.0
        self.bet_modes = []
        self.rtp = 0.0

        for name, difficulty in DIFFICULTIES.items():
            cols = difficulty["cols"]
            win_count = difficulty["win_count"]
            rows = difficulty["rows"]
            mines = mines_for(cols, win_count)
            # Published ladder: fair odds × depth house edge.
            steps = build_row_steps(cols, win_count, rows)
            multipliers = build_multipliers(cols, win_count, rows)
            bonuses = {
                str(idx): {str(m): odds for m, odds in table.items()}
                for idx, table in bonuses_for_difficulty(rows).items()
            }
            bonus_chances = bonus_chances_for_difficulty(bonuses, cols, win_count, rows)
            mode_rtp = round(session_rtp(cols, win_count, rows), 4)
            base_mode = {
                "label": difficulty["label"],
                "cols": cols,
                "mines": mines,
                "winCount": win_count,
                "rows": rows,
                "winChance": win_chance(cols, win_count),
                "sessionRtp": mode_rtp,
                "maxWin": multipliers[-1],
                "maxWinning": self.max_payout,
                "maxBet": self.max_bet,
                "firstMultiplier": multipliers[0],
                "rowSteps": steps,
                "bonuses": bonuses,
                "bonusChances": bonus_chances,
                "multipliers": multipliers,
                "baseDifficulty": name,
            }
            self.tower_modes[name] = {
                **base_mode,
                # Open round at Start — initial 1× (payout = bet).
                "sessionOpen": True,
                "settleTarget": "session",
                "settlePayout": 1.0,
            }
            self.wincap = max(self.wincap, base_mode["maxWin"])
            if self.rtp == 0.0 or mode_rtp < self.rtp:
                self.rtp = mode_rtp

            # Session-open mode (play on Start Session).
            self.bet_modes.append(
                BetMode(
                    name=name,
                    cost=1.0,
                    rtp=0.0,
                    # 1x base + jitter headroom (0.9 / 1.0 / 1.1).
                    max_win=1.2,
                    auto_close_disabled=True,
                    is_feature=True,
                    is_buybonus=False,
                    distributions=[
                        Distribution(
                            criteria="basegame",
                            quota=1.0,
                            conditions={
                                "reel_weights": {},
                                "force_wincap": False,
                                "force_freegame": False,
                            },
                        ),
                    ],
                )
            )

            # Loss settle
            loss_name = f"{name}_loss"
            self.tower_modes[loss_name] = {
                **base_mode,
                "settleTarget": "loss",
                "settlePayout": 0.0,
                "maxWin": 0.2,
            }
            self.bet_modes.append(
                BetMode(
                    name=loss_name,
                    cost=1.0,
                    rtp=0.0,
                    max_win=0.2,
                    auto_close_disabled=True,
                    is_feature=True,
                    is_buybonus=False,
                    distributions=[
                        Distribution(
                            criteria="basegame",
                            quota=1.0,
                            conditions={
                                "reel_weights": {},
                                "force_wincap": False,
                                "force_freegame": False,
                            },
                        ),
                    ],
                )
            )

            # Cashout settle — one mode per cleared-row depth (bare ladder).
            for depth, mult in enumerate(multipliers, start=1):
                settle_name = f"{name}_{depth}"
                settle_cap = round(float(mult) + 0.2, 1)
                self.tower_modes[settle_name] = {
                    **base_mode,
                    "settleTarget": depth,
                    "settlePayout": mult,
                    "maxWin": settle_cap,
                }
                self.bet_modes.append(
                    BetMode(
                        name=settle_name,
                        cost=1.0,
                        rtp=mode_rtp,
                        max_win=settle_cap,
                        auto_close_disabled=True,
                        is_feature=True,
                        is_buybonus=False,
                        distributions=[
                            Distribution(
                                criteria="basegame",
                                quota=1.0,
                                conditions={
                                    "reel_weights": {},
                                    "force_wincap": False,
                                    "force_freegame": False,
                                },
                            ),
                        ],
                    )
                )

            # Bonus-aware settle — every ladder×bonus-product payout Stake needs.
            # Client cashout with a collected ×2 on 2.2 plays ``easy_p440`` (4.4×).
            for payout in enumerate_settle_payouts(multipliers, bonuses):
                settle_name = settle_mode_name(name, payout)
                if settle_name in self.tower_modes:
                    continue
                settle_cap = round(float(payout) + 0.2, 1)
                self.wincap = max(self.wincap, float(payout))
                self.tower_modes[settle_name] = {
                    **base_mode,
                    "settleTarget": "payout",
                    "settlePayout": float(payout),
                    "maxWin": settle_cap,
                }
                self.bet_modes.append(
                    BetMode(
                        name=settle_name,
                        cost=1.0,
                        rtp=mode_rtp,
                        max_win=settle_cap,
                        auto_close_disabled=True,
                        is_feature=True,
                        is_buybonus=False,
                        distributions=[
                            Distribution(
                                criteria="basegame",
                                quota=1.0,
                                conditions={
                                    "reel_weights": {},
                                    "force_wincap": False,
                                    "force_freegame": False,
                                },
                            ),
                        ],
                    )
                )

        self.tower_rows = max(
            m["rows"] for name, m in self.tower_modes.items() if name in DIFFICULTIES
        )

        self.construct_paths()

        self.num_reels = 0
        self.num_rows = [0] * self.num_reels
        self.paytable = {}
        self.include_padding = False
        self.special_symbols = {"wild": [], "scatter": [], "multiplier": []}

        self.freespin_triggers = {self.basegame_type: {}, self.freegame_type: {}}
        self.anticipation_triggers = {self.basegame_type: 0, self.freegame_type: 0}
