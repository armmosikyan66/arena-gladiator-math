import json
from pathlib import Path

math = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno")
app = Path("/Users/edgar/Documents/GitHub/lumen-keno/src/data")
pay = json.loads((math / "paytables.json").read_text())
front = json.loads((app / "keno-paytables.json").read_text())
books = json.loads((app / "keno-books.json").read_text())

assert max(pay["risks"]["high"]["10"]) == 50000.0
assert pay["risks"]["high"]["1"] == [0.1, 3.5]
assert front["risks"]["high"]["10"][-1] == 50000.0
assert max(r["payout"] for r in books["modes"]["high_pick_10"]["books"]) / 100 == 50000.0

assert pay["earn"]["high"]["10"][-1] == 25000.0
assert front["earn"]["high"]["10"][-1] == 25000.0
earn_how = max(r["payout"] for r in books["modes"]["high_pick_10_earn"]["books"]) / 100
assert earn_how == 100000.0, earn_how
assert pay["earn"]["high"]["1"] == [0.5, 2.1]

assert pay["earn"]["medium"]["10"][-1] == 5000.0
assert front["earn"]["medium"]["10"][-1] == 5000.0
med_how = max(r["payout"] for r in books["modes"]["medium_pick_10_earn"]["books"]) / 100
assert med_how == 30000.0, med_how

assert pay["buy10"]["medium"]["10"][-1] == 1500.0
assert pay["buy100"]["medium"]["10"][-1] == 300.0
assert front["buy10"]["medium"]["10"][-1] == 1500.0
assert front["buy100"]["medium"]["10"][-1] == 300.0

assert pay["earn"]["classic"]["10"][-1] == 1000.0
assert front["earn"]["classic"]["10"][-1] == 1000.0

assert "def patch_earn_high" in (math / "solve_paytables.py").read_text()
assert "HIGH_EARN_TOP" in (math / "solve_paytables.py").read_text()
assert (math / "export_earn_high_books.py").exists()
assert (math / "run_earn_high.py").exists()

print("Off high pick 10", pay["risks"]["high"]["10"][-1])
print("Earn high pick 10 advertised", pay["earn"]["high"]["10"][-1], "How-to", earn_how)
print("Earn medium pick 10", pay["earn"]["medium"]["10"][-1], "How-to", med_how)
print("Buy medium pick 10", pay["buy10"]["medium"]["10"][-1], pay["buy100"]["medium"]["10"][-1])
print("classic earn 10", pay["earn"]["classic"]["10"][-1])
print("MAC_EARN_HIGH_OK")
