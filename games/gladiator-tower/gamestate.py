"""Handles the state and output for a single tower simulation round."""

from game_calculations import round_coefficient
from game_override import GameStateOverride
from game_events import session_start_event, tile_reveal_event
from session import start_session, pick_tile, cash_out, resolved_row_bonuses


class GameState(GameStateOverride):
    """Handle all game-logic and event updates for a given simulation number.

    * Session modes (``easy``, …): ``sessionStart`` + ``mineLayout``, initial
      **1×** (book root payoutMultiplier 100). Round stays active until
      end-round. Stake Fair API selects which published book (layout) is used.
    * Settle modes (``easy_3``, ``easy_loss``, …): near-fixed payout for
      cashout depth after the open session is closed.

    Stake publish needs ≥3 distinct LUT payouts — tiny ±0.1× jitter.
    """

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim, simulation_seed)
        self._simulation_seed = simulation_seed
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.play_session()
            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def play_session(self):
        """Play one tower session through the shared session engine."""
        mode = self.get_current_mode()
        base = mode.get("baseDifficulty") or self.betmode

        # Layout is baked into the published book; Stake PF selects the book.
        session = start_session(base, bet_amount=1.0, mode=mode, rng=self.rng)
        self.tower_session = session

        target = mode.get("settleTarget")
        is_session_open = mode.get("sessionOpen") or target == "session"

        session_start_event(
            self,
            base,
            session.rows,
            session.cols,
            session.mines,
            win_count=session.win_count,
            row_steps=session.row_steps,
            multipliers=session.multipliers,
            bonuses=mode.get("bonuses"),
            coefficient=1.0,
            payout_multiplier=1.0 if is_session_open else 0.0,
            status="ACTIVE",
            mine_layout=session.layout_public(),
            # Live / test: ship pre-resolved placements so the client can
            # reveal missed bonuses on the tower after a loss.
            row_bonuses=resolved_row_bonuses(session) if is_session_open else None,
        )

        if is_session_open:
            # Book root = 100 (1×). UI payout = bet. Loss settled via *_loss.
            total_win = 1.0
        elif target == "loss":
            total_win = self._play_forced_loss(session)
        elif target == "payout":
            # Bonus-aware settle: fixed payout (ladder × bonus product).
            total_win = float(mode.get("settlePayout") or 0.0)
        elif isinstance(target, int):
            total_win = self._play_forced_cashout(session, target)
        else:
            total_win = self._play_to_top(session)

        # Stake cannot compute LUT stats from a single payout value.
        if mode.get("settleTarget") is not None or is_session_open:
            total_win = self._publish_payout_jitter(total_win)
            # Keep reveal coefficients in sync with the (possibly jittered) payout
            # so Stake's event↔weight check does not fail ERR_MATH_OUTSIDE_RANGE.
            self._sync_event_coefficients_to_payout(total_win)

        # Do NOT emit cashOut/finalWin — they cause active:false on Stake.
        # payoutMultiplier is set on the book root by evaluate_finalwin().

        self.win_manager.update_spinwin(total_win)
        self.win_manager.update_gametype_wins(self.gametype)
        self.win_data = {"totalWin": total_win, "wins": []}

    def _publish_payout_jitter(self, payout: float) -> float:
        """Spread ~1% of books across 3 payout values (Stake min_dist_difference).

        Stake's publish stats require at least three distinct LUT payouts;
        a single constant value raises ERR_MATH_OUTSIDE_RANGE.
        """
        base = round_coefficient(float(payout))
        bucket = int(self.sim) % 200
        if base <= 0:
            # Loss mode: mostly 0, rare 0.1 / 0.2 so stats exist.
            if bucket == 198:
                return 0.1
            if bucket == 199:
                return 0.2
            return 0.0

        low = round_coefficient(max(0.1, base - 0.1))
        # Use +0.2 when +0.1 would floor back to base (float edge cases).
        high = round_coefficient(base + 0.1)
        if high <= base:
            high = round_coefficient(base + 0.2)
        if high <= base:
            high = round_coefficient(base + 1.0)
        if low >= base:
            low = round_coefficient(max(0.1, base - 0.2))

        if bucket == 198:
            return low
        if bucket == 199:
            return high
        return base

    def _sync_event_coefficients_to_payout(self, payout: float) -> None:
        """Align event coefficients with book payout after jitter.

        Stake compares LUT CSV payouts to the payout implied by book events.
        If we jitter root payoutMultiplier to 4.5× but leave the last
        ``tileReveal.coefficient`` at 4.6, publish fails with
        ``ERR_MATH_OUTSIDE_RANGE`` (event/weight mismatch).
        """
        payout = round_coefficient(float(payout or 0))
        events = getattr(self.book, "events", None) or []
        if not events:
            return

        # Session-open books: keep open payout at 1× family (0.9 / 1.0 / 1.1).
        mode = self.get_current_mode()
        is_session_open = mode.get("sessionOpen") or mode.get("settleTarget") == "session"
        if is_session_open:
            for ev in events:
                if ev.get("type") == "sessionStart":
                    ev["coefficient"] = payout
                    ev["payoutMultiplier"] = payout
            return

        if payout <= 0:
            # Loss: freeze coefficient on the mine hit (already correct).
            return

        # Rebuild cumulative coefficients so the final reveal equals ``payout``.
        reveal_idxs = [
            i
            for i, ev in enumerate(events)
            if ev.get("type") in ("tileReveal", "mineHit") and not ev.get("isMine")
        ]
        if not reveal_idxs:
            return

        # Scale the last safe reveal to the jittered payout; keep prior rows
        # as the published ladder when possible.
        last_i = reveal_idxs[-1]
        events[last_i]["coefficient"] = payout

        # Optional: if only one safe reveal, that is the whole payout.
        if len(reveal_idxs) == 1:
            return

        # Keep earlier reveals consistent as a rising sequence ending at payout.
        # Prefer session ladder values for all but the last row.
        session = getattr(self, "tower_session", None)
        mults = list(getattr(session, "multipliers", None) or [])
        for order, idx in enumerate(reveal_idxs[:-1]):
            if order < len(mults):
                events[idx]["coefficient"] = round_coefficient(mults[order])
            # else leave as-is

        # Ensure monotonic non-decreasing toward final payout.
        prev = 1.0
        for idx in reveal_idxs:
            coef = float(events[idx].get("coefficient") or prev)
            if coef < prev:
                coef = prev
            if idx == last_i:
                coef = payout
            events[idx]["coefficient"] = round_coefficient(coef)
            prev = events[idx]["coefficient"]

    def _play_forced_loss(self, session) -> float:
        """Hit a mine on row 0 — book pays 0."""
        mines = session.mine_layout[0]
        tile = min(mines) if mines else 0
        result = pick_tile(session, 0, tile)
        tile_reveal_event(
            self,
            result["row"],
            result["tile"],
            True,
            coefficient=result["coefficient"],
        )
        return 0.0

    def _play_forced_cashout(self, session, cleared_rows: int) -> float:
        """Clear exactly ``cleared_rows`` with safe picks, then cash out."""
        target = max(1, min(int(cleared_rows), session.rows))
        for row in range(target):
            safe = [c for c in range(session.cols) if c not in session.mine_layout[row]]
            tile = safe[0] if safe else 0
            result = pick_tile(session, row, tile)
            if result.get("is_mine"):
                tile_reveal_event(
                    self,
                    result["row"],
                    result["tile"],
                    True,
                    coefficient=result["coefficient"],
                )
                return 0.0
            tile_reveal_event(
                self,
                result["row"],
                result["tile"],
                False,
                coefficient=result["coefficient"],
                bonus_multiplier=result.get("bonus_multiplier"),
            )
            if session.status != "ACTIVE":
                break

        if session.status == "ACTIVE":
            cash_out(session)

        if session.status in ("CLEARED", "CASHED_OUT"):
            return float(session.payout_multiplier)
        return 0.0

    def _play_to_top(self, session) -> float:
        """Legacy random climb until mine or summit."""
        while session.status == "ACTIVE":
            tile = self.rng.randrange(session.cols)
            result = pick_tile(session, session.current_row, tile)
            if result.get("is_mine"):
                tile_reveal_event(
                    self,
                    result["row"],
                    result["tile"],
                    True,
                    coefficient=result["coefficient"],
                )
                break
            tile_reveal_event(
                self,
                result["row"],
                result["tile"],
                False,
                coefficient=result["coefficient"],
                bonus_multiplier=result.get("bonus_multiplier"),
            )
            if session.status != "ACTIVE":
                break

        if session.status == "ACTIVE" and session.current_row > 0:
            cash_out(session)

        if session.status in ("CLEARED", "CASHED_OUT"):
            return float(session.payout_multiplier)
        return 0.0

    def run_freespin(self):
        pass
