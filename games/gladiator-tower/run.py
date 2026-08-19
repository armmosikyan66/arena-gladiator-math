"""Entry point for Gladiator Tower math outputs."""

import hashlib
import json
import os
import pickle
import shutil

from gamestate import GameState
from game_config import GameConfig
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from src.write_data.write_data import get_sha_256


def export_fe_math_config(config, gamestate):
    """Write a machine-readable math config the web client can consume directly."""
    # Only base difficulties (easy/medium/…) — not settle modes like easy_3.
    base_names = set(config.difficulties.keys())
    payload = {
        "gameId": config.game_id,
        "gameName": config.game_name,
        "houseEdge": config.house_edge,
        "edgeGrowth": 0.002,
        "minBet": 1.0,
        "maxBet": 10.0,
        "betStep": 1.0,
        # Max win exposure (dollars). Truncates tower; ladder is fair-odds.
        "maxPayout": getattr(config, "max_payout", 10_000.0),
        "minPlayableRows": 1,
        "difficulties": {
            name: {
                "label": mode["label"],
                "cols": mode["cols"],
                "mines": mode["mines"],
                "winCount": mode["winCount"],
                "rows": mode["rows"],
                "winChance": mode["winChance"],
                "sessionRtp": mode["sessionRtp"],
                "maxWin": mode["maxWin"],
                "maxWinning": mode.get(
                    "maxWinning", getattr(config, "max_payout", 10_000.0)
                ),
                "rowSteps": mode["rowSteps"],
                "bonuses": mode["bonuses"],
                "bonusChances": mode.get("bonusChances", []),
                "multipliers": mode["multipliers"],
            }
            for name, mode in config.tower_modes.items()
            if name in base_names
        },
    }
    out_path = os.path.join(gamestate.output_files.config_path, "math_config.json")
    with open(out_path, "w", encoding="UTF-8") as out_file:
        json.dump(payload, out_file, indent=2)

    # Keep the web client ladder in sync when regenerating books.
    fe_path = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "web",
            "src",
            "data",
            "tower-math-config.json",
        )
    )
    if os.path.isdir(os.path.dirname(fe_path)):
        with open(fe_path, "w", encoding="UTF-8") as out_file:
            json.dump(payload, out_file, indent=2)
        print(f"[export] synced FE math config → {fe_path}")
    return out_path


def sync_publish_lookups(gamestate):
    """Force-refresh publish LUTs + verification sidecars from the latest books.

    The SDK only copies ``lookUpTable_<mode>_0.csv`` when the file is missing,
    so a math change leaves stale optimized LUTs that fail Stake's
    ``ERR_MATH_OUTSIDE_RANGE`` (LUT payout ≠ book payoutMultiplier).
    """
    for betmode in gamestate.config.bet_modes:
        name = betmode.get_name()
        base_lut = gamestate.output_files.get_final_lookup_name(name)
        opt_lut = gamestate.output_files.get_optimized_lookup_name(name)
        book_file = gamestate.output_files.get_final_book_name(name, compress=True)
        if not os.path.exists(book_file):
            book_file = gamestate.output_files.get_final_book_name(name, compress=False)
        if not os.path.exists(base_lut):
            print(f"[sync] skip {name}: missing base LUT {base_lut}")
            continue

        shutil.copy(base_lut, opt_lut)
        print(f"[sync] refreshed {opt_lut}")

        payouts = []
        with open(opt_lut, "r", encoding="UTF-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    payouts.append(int(parts[2]))

        if os.path.exists(book_file):
            verification = {
                "payout_hash": hashlib.md5(pickle.dumps(payouts)).hexdigest(),
                "file_hash": get_sha_256(book_file),
                "num_entries": len(payouts),
            }
            verification_path = os.path.join(
                gamestate.output_files.config_path, f"books_{name}.verification.json"
            )
            with open(verification_path, "w", encoding="UTF-8") as f:
                json.dump(verification, f, indent=2)
            print(f"[sync] wrote {verification_path} ({len(payouts)} entries)")


def verify_stake_publish(gamestate) -> bool:
    """Ensure every file referenced by index.json exists in publish_files/."""
    manifest_path = gamestate.output_files.configs["paths"]["manifest"]
    publish_dir = gamestate.output_files.publish_path
    ok = True

    if not os.path.isfile(manifest_path):
        print(f"[publish] MISSING manifest: {manifest_path}")
        return False

    with open(manifest_path, "r", encoding="UTF-8") as f:
        manifest = json.load(f)

    required = {"index.json"}
    for mode in manifest.get("modes", []):
        for key in ("events", "weights"):
            name = mode.get(key)
            if name:
                required.add(name)

    print(f"[publish] Stake upload folder (all {len(required)} files required):")
    print(f"  {publish_dir}")
    for filename in sorted(required):
        path = os.path.join(publish_dir, filename)
        if not os.path.isfile(path):
            print(f"  ✗ MISSING: {filename}")
            ok = False
            continue
        size = os.path.getsize(path)
        if size == 0:
            print(f"  ✗ EMPTY: {filename}")
            ok = False
        else:
            print(f"  ✓ {filename} ({size:,} bytes)")

    easy_book = os.path.join(publish_dir, "books_easy.jsonl.zst")
    if os.path.isfile(easy_book):
        try:
            import zstandard as zst

            with open(easy_book, "rb") as bf:
                reader = zst.ZstdDecompressor().stream_reader(bf)
                line = reader.read().splitlines()[0]
            sample = json.loads(line)
            ev = sample.get("events") or []
            types = [e.get("type") for e in ev]
            pm = sample.get("payoutMultiplier")
            has_layout = any(
                e.get("type") == "sessionStart" and e.get("mineLayout") for e in ev
            )
            if types == ["sessionStart"] and int(pm or 0) in (90, 100, 110):
                layout_note = "with mineLayout" if has_layout else "WARN missing mineLayout"
                print(
                    f"[publish] Session-open book OK "
                    f"(sessionStart only, payoutMultiplier={pm} ≈ 1×, {layout_note})."
                )
            elif types == ["sessionStart"]:
                print(
                    f"[publish] WARN session book payoutMultiplier={pm} "
                    f"— expected ~100 (1×)."
                )
            else:
                print(f"[publish] WARN book event types {types!r} — expected ['sessionStart'].")
            if types == ["sessionStart"] and not has_layout:
                print(
                    "[publish] WARN: sessionStart needs mineLayout for Stake Fair API."
                )
        except Exception as exc:
            print(f"[publish] Could not sample books_easy: {exc}")

    if not ok:
        print(
            "\n[publish] Fix: from math/games run "
            "`python3 gladiator-tower/run.py` and upload the entire publish_files/ "
            "directory (not configs/ or web/dist). library/ is gitignored."
        )
    return ok


if __name__ == "__main__":

    num_threads = 1
    batching_size = 50000
    compression = True
    profiling = False

    config = GameConfig()
    # Settle modes are deterministic (fixed payout) — fewer sims keep publish lean.
    # Bonus-aware ``*_p{N}`` modes need even fewer (constant payout + jitter).
    num_sim_args = {}
    for bm in config.bet_modes:
        name = bm.get_name()
        if "_p" in name and name.split("_p")[-1].isdigit():
            num_sim_args[name] = 400
        elif name.endswith("_loss") or name.rsplit("_", 1)[-1].isdigit():
            num_sim_args[name] = 800
        else:
            num_sim_args[name] = int(2e3)

    run_conditions = {"run_sims": True}

    gamestate = GameState(config)

    if run_conditions["run_sims"]:
        # Drop stale optimized LUTs so a math change cannot leave old payouts.
        for betmode in config.bet_modes:
            opt = gamestate.output_files.get_optimized_lookup_name(betmode.get_name())
            if os.path.exists(opt):
                os.remove(opt)
                print(f"[run] removed stale {opt}")

        # Remove obsolete base-mode publish artifacts (easy → easy_1 / easy_loss).
        publish_dir = gamestate.output_files.publish_path
        if os.path.isdir(publish_dir):
            keep = set()
            for name in num_sim_args:
                keep.add(f"books_{name}.jsonl.zst")
                keep.add(f"lookUpTable_{name}_0.csv")
            keep.add("index.json")
            for filename in os.listdir(publish_dir):
                if filename.startswith(("books_", "lookUpTable_")) and filename not in keep:
                    path = os.path.join(publish_dir, filename)
                    os.remove(path)
                    print(f"[run] removed obsolete {filename}")

        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )
    generate_configs(gamestate)
    export_fe_math_config(config, gamestate)
    sync_publish_lookups(gamestate)
    if not verify_stake_publish(gamestate):
        raise SystemExit(1)
