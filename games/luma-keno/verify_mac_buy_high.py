import json
from pathlib import Path

math = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno")
app = Path("/Users/edgar/Documents/GitHub/lumen-keno/src/data")
pay = json.loads((math / "paytables.json").read_text())
front = json.loads((app / "keno-paytables.json").read_text())
books = json.loads((app / "keno-books.json").read_text())
solve = (math / "solve_paytables.py").read_text()

assert max(pay["risks"]["high"]["10"]) == 50000.0
assert front["risks"]["high"]["10"][-1] == 50000.0
assert max(r["payout"] for r in books["modes"]["high_pick_10"]["books"]) / 100 == 50000.0

assert pay["earn"]["high"]["10"][-1] == 25000.0
assert front["earn"]["high"]["10"][-1] == 25000.0
earn_how = max(r["payout"] for r in books["modes"]["high_pick_10_earn"]["books"]) / 100
assert earn_how == 100000.0, earn_how

assert pay["buy10"]["high"]["10"][-1] == 2250.0, pay["buy10"]["high"]["10"][-1]
assert pay["buy100"]["high"]["10"][-1] == 450.0, pay["buy100"]["high"]["10"][-1]
assert front["buy10"]["high"]["10"][-1] == 2250.0
assert front["buy100"]["high"]["10"][-1] == 450.0

b10 = books["modes"]["high_pick_10_buy10"]
b100 = books["modes"]["high_pick_10_buy100"]
how10 = max(r["payout"] for r in b10["books"]) / 100
how100 = max(r["payout"] for r in b100["books"]) / 100
assert abs(how10 / b10["cost"] - 4500.0) < 1e-6, how10
assert abs(how100 / b100["cost"] - 900.0) < 1e-6, how100

assert pay["earn"]["medium"]["10"][-1] == 5000.0
assert front["earn"]["medium"]["10"][-1] == 5000.0
assert pay["buy10"]["medium"]["10"][-1] == 1500.0
assert pay["buy100"]["medium"]["10"][-1] == 300.0
assert pay["earn"]["classic"]["10"][-1] == 1000.0
assert front["earn"]["classic"]["10"][-1] == 1000.0

assert "def is_easy_buy_high(" in solve
assert "def easy_buy_high_top(" in solve
assert "def patch_buy_high(" in solve
assert "--buy-high" in solve
assert "PULSE_BOOST[\"high\"]" in solve
assert (math / "export_buy_high_books.py").exists()
assert (math / "run_buy_high.py").exists()

print("Off high pick 10", pay["risks"]["high"]["10"][-1])
print("Earn high pick 10 advertised", pay["earn"]["high"]["10"][-1], "How-to", earn_how)
print("Buy high pick 10 JSON", pay["buy10"]["high"]["10"][-1], pay["buy100"]["high"]["10"][-1])
print("Buy high pick 10 of-the-buy", how10 / b10["cost"], how100 / b100["cost"])
print("Earn medium pick 10", pay["earn"]["medium"]["10"][-1])
print("Buy medium pick 10", pay["buy10"]["medium"]["10"][-1], pay["buy100"]["medium"]["10"][-1])
print("classic earn 10", pay["earn"]["classic"]["10"][-1])
print("MAC_BUY_HIGH_OK")
