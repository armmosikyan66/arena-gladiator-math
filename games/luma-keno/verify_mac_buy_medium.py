import json
from pathlib import Path

math_pay = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno/paytables.json")
front = Path("/Users/edgar/Documents/GitHub/lumen-keno/src/data/keno-paytables.json")
books = Path("/Users/edgar/Documents/GitHub/lumen-keno/src/data/keno-books.json")
solve = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno/solve_paytables.py")
run = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno/run_buy_medium.py")
export = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno/export_buy_medium_books.py")

for p in (math_pay, front, books, solve, run, export):
    print(f"exists {p.exists()} {p}")

p = json.loads(math_pay.read_text())
f = json.loads(front.read_text())
b = json.loads(books.read_text())["modes"]

print("math buy10 medium 10", p["buy10"]["medium"]["10"])
print("math buy100 medium 10", p["buy100"]["medium"]["10"])
print("front buy10 medium 10", f["buy10"]["medium"]["10"])
print("front buy100 medium 10", f["buy100"]["medium"]["10"])
assert f["buy10"]["medium"]["10"] == p["buy10"]["medium"]["10"]
assert f["buy100"]["medium"]["10"] == p["buy100"]["medium"]["10"]
assert max(f["buy10"]["medium"]["10"]) == 2250.0
assert max(f["buy100"]["medium"]["10"]) == 450.0

# certified unchanged
print("front off medium 10", max(f["risks"]["medium"]["10"]))
print("front earn medium 10", max(f["earn"]["medium"]["10"]))
print("front buy10 classic 10", max(f["buy10"]["classic"]["10"]))
print("front buy100 classic 10", max(f["buy100"]["classic"]["10"]))
print("front buy10 low 10", max(f["buy10"]["low"]["10"]))
assert max(f["risks"]["medium"]["10"]) == 5000.0
assert max(f["earn"]["medium"]["10"]) == 5000.0
assert max(f["earn"]["classic"]["10"]) == 1000.0
assert max(f["buy10"]["classic"]["10"]) == 1000.0
assert max(f["buy100"]["classic"]["10"]) == 450.0
assert max(f["buy10"]["low"]["10"]) == 100.0

for name in (
    "medium_pick_10",
    "medium_pick_10_earn",
    "medium_pick_10_buy10",
    "medium_pick_10_buy100",
    "classic_pick_10_earn",
    "classic_pick_10_buy10",
    "low_pick_10_buy10",
):
    m = b[name]
    how = max(r["payout"] for r in m["books"]) / 100
    cost = m["cost"]
    print(f"{name:28s} rtp={m['rtp']:.4f} how_base={how:.1f} of_buy={how/cost:.1f} n={len(m['books'])}")

assert abs(max(r["payout"] for r in b["medium_pick_10"]["books"]) / 100 - 5000.0) < 1e-6
assert abs(max(r["payout"] for r in b["medium_pick_10_earn"]["books"]) / 100 - 20000.0) < 1e-6
assert abs(max(r["payout"] for r in b["classic_pick_10_earn"]["books"]) / 100 - 4000.0) < 1e-6
assert abs(max(r["payout"] for r in b["medium_pick_10_buy10"]["books"]) / 100 / 10 - 4500.0) < 1e-6
assert abs(max(r["payout"] for r in b["medium_pick_10_buy100"]["books"]) / 100 / 100 - 900.0) < 1e-6

text = solve.read_text()
assert "def is_easy_buy_medium(" in text
assert "def easy_buy_medium_top(" in text
assert "def patch_buy_medium(" in text
assert "--buy-medium" in text
print("MAC_OK")
