"""Keno book events."""

from src.events.events import set_total_event, set_win_event


def keno_start_event(
    gamestate,
    risk: str,
    picks_count: int,
    pay_row: list[float],
    lumen_boost: float,
    lumen_marked: bool,
    pulse_boost: float,
    lumen_placed: bool = False,
) -> None:
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": "kenoStart",
            "risk": risk,
            "picksCount": picks_count,
            "drawnCount": gamestate.config.keno_drawn,
            "poolSize": gamestate.config.keno_pool,
            "paytable": pay_row,
            "lumenMarked": bool(lumen_marked),
            "lumenBoost": lumen_boost,
            "pulseBoost": pulse_boost,
            "lumenPlaced": bool(lumen_placed),
        }
    )


def keno_catch_event(
    gamestate,
    main_hits: int,
    total_hits: int,
    multiplier: float,
    lumen_hit: bool,
    extras: bool,
    extra_reason: str | None,
    extra_hits: int,
    lumen_boost: float,
    pulse: float,
) -> None:
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": "kenoCatch",
            "hits": total_hits,
            "mainHits": main_hits,
            "multiplier": multiplier,
            "lumenHit": bool(lumen_hit),
            "lumenBoost": lumen_boost,
            "extrasOpened": bool(extras),
            "extraHits": extra_hits if extras else 0,
            "extraReason": extra_reason,
            "pulse": pulse,
        }
    )


def keno_win_events(gamestate) -> None:
    set_win_event(gamestate)
    set_total_event(gamestate)
    gamestate.evaluate_finalwin()
