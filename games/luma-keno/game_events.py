"""Keno book events."""

from src.events.events import set_total_event, set_win_event


def keno_start_event(gamestate, risk: str, picks_count: int, pay_row: list[float]) -> None:
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": "kenoStart",
            "risk": risk,
            "picksCount": picks_count,
            "drawnCount": gamestate.config.keno_drawn,
            "poolSize": gamestate.config.keno_pool,
            "paytable": pay_row,
        }
    )


def keno_catch_event(gamestate, hits: int, multiplier: float) -> None:
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": "kenoCatch",
            "hits": hits,
            "multiplier": multiplier,
        }
    )


def keno_win_events(gamestate) -> None:
    set_win_event(gamestate)
    set_total_event(gamestate)
    gamestate.evaluate_finalwin()
