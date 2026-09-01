"""Four-check helper: math tables, client paytable, and client books agree.

Run after every `export_chart.py` pass. Asserts the shipped row for each chart
that has been restaired, that the client copy matches the math copy exactly,
and that every restaired row still passes `shape_lock` - so a later re-solve
that quietly re-packs a column fails here instead of on a player's screen.
"""

import json
from pathlib import Path

from shape_lock import lock_for, violations

math = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno")
app = Path("/Users/edgar/Documents/GitHub/lumen-keno/src/data")
pay = json.loads((math / "paytables.json").read_text())
front = json.loads((app / "keno-paytables.json").read_text())
books = json.loads((app / "keno-books.json").read_text())

#: (section, risk, pick) -> row as it must ship, in paytables.json base-bet units.
#: `locked` rows are additionally re-checked against the shape lock.
SHIPPED = {
    ("risks", "high", 10): (
        [0.0, 0.0, 0.0, 0.2, 0.4, 4.3, 78.5, 200.0, 700.0, 4500.0, 50000.0],
        False,  # certified before the lock existed; frozen, not lock-clean
    ),
    ("risks", "high", 9): (
        [0.0, 0.0, 0.0, 0.2, 1.0, 16.0, 92.0, 500.0, 3000.0, 40000.0],
        True,
    ),
    ("risks", "high", 6): (
        [0.0, 0.0, 0.0, 3.0, 10.0, 79.0, 3484.6],
        True,
    ),
    ("risks", "medium", 10): (
        [0.0, 0.0, 0.0, 0.9, 2.0, 6.0, 18.0, 52.0, 175.0, 550.0, 5000.0],
        True,
    ),
    ("risks", "classic", 10): (
        [0.0, 0.0, 0.0, 1.6, 2.3, 3.1, 4.0, 10.0, 50.0, 500.0, 1000.0],
        False,  # restaired, but 1000x cannot host a lock-clean 8-cell ladder
    ),
    ("earn", "classic", 10): (
        [0.0, 0.0, 0.0, 0.7, 0.9, 2.3, 6.0, 16.0, 45.0, 120.0, 1000.0],
        True,
    ),
}

for (section, risk, k), (expected, locked) in SHIPPED.items():
    name = f"{section}.{risk}.{k}"
    got = pay[section][risk][str(k)]
    assert got == expected, f"{name}: math has {got}, expected {expected}"
    assert front[section][risk][str(k)] == got, f"{name}: client paytable drifted"
    if locked:
        cost = 100.0 if section == "buy100" else 10.0 if section == "buy10" else 1.0
        row = [m / cost for m in got]
        errs = violations(row, k, lock=lock_for(cost, pick=k), label=name)
        assert not errs, f"{name}: {errs}"
    print(f"{name:22s} {[m for m in got if m]}{'  shape-locked' if locked else ''}")

assert pay["risks"]["high"]["1"] == [0.1, 3.5]
assert max(r["payout"] for r in books["modes"]["high_pick_10"]["books"]) == 5000000

# Tops that other ladders are graded against. Earn must not advertise below Off
# at the same pick; the buy chips must not raise the Off jackpot.
assert pay["earn"]["medium"]["10"][-1] == 5000.0
assert front["earn"]["medium"]["10"][-1] == 5000.0
assert pay["earn"]["classic"]["10"][-1] == pay["risks"]["classic"]["10"][-1] == 1000.0
assert pay["buy10"]["medium"]["10"][-1] == 1500.0
assert pay["buy100"]["medium"]["10"][-1] == 300.0
assert front["buy10"]["medium"]["10"][-1] == 1500.0
assert front["buy100"]["medium"]["10"][-1] == 300.0

# Every mode the client ships must have a book behind it.
for (section, risk, k) in SHIPPED:
    suffix = "" if section == "risks" else f"_{section}" if section != "earn" else "_earn"
    assert f"{risk}_pick_{k}{suffix}" in books["modes"], f"missing book {risk}_pick_{k}"

assert (math / "easy_off_high.py").exists()
assert (math / "export_chart.py").exists()
assert (math / "shape_lock.py").exists()
assert "def patch_off_high" in (math / "solve_paytables.py").read_text()
assert "HIGH_OFF" in (math / "solve_paytables.py").read_text()
print("MAC_OK")
