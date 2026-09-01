import json
from pathlib import Path

math = Path("/Users/edgar/Documents/GitHub/lumen-keno-math/games/luma-keno")
app = Path("/Users/edgar/Documents/GitHub/lumen-keno/src/data")
pay = json.loads((math / "paytables.json").read_text())
front = json.loads((app / "keno-paytables.json").read_text())
books = json.loads((app / "keno-books.json").read_text())

high10 = pay["risks"]["high"]["10"]
print("Off high pick 10", high10, "max", max(high10))
assert max(high10) == 50000.0
assert high10 == [0.0, 0.0, 0.0, 1.9, 2.0, 2.3, 2.7, 3.0, 90.0, 4500.0, 50000.0]
assert pay["risks"]["high"]["1"] == [0.1, 3.5]
assert front["risks"]["high"]["10"] == high10
assert max(r["payout"] for r in books["modes"]["high_pick_10"]["books"]) == 5000000

earn_med10 = pay["earn"]["medium"]["10"]
print("Earn medium pick 10", earn_med10[-1], "How-to", earn_med10[-1] * 6)
assert earn_med10[-1] == 5000.0
assert front["earn"]["medium"]["10"][-1] == 5000.0

buy10 = pay["buy10"]["medium"]["10"][-1]
buy100 = pay["buy100"]["medium"]["10"][-1]
print("Buy medium pick 10", buy10, buy100)
assert buy10 == 1500.0
assert buy100 == 300.0
assert front["buy10"]["medium"]["10"][-1] == 1500.0
assert front["buy100"]["medium"]["10"][-1] == 300.0

classic_earn = pay["earn"]["classic"]["10"][-1]
print("classic earn 10", classic_earn)
assert classic_earn == 1000.0
assert front["earn"]["classic"]["10"][-1] == 1000.0

assert (math / "easy_off_high.py").exists()
assert (math / "export_off_high_books.py").exists()
assert (math / "run_off_high.py").exists()
assert "def patch_off_high" in (math / "solve_paytables.py").read_text()
assert "HIGH_OFF" in (math / "solve_paytables.py").read_text()
print("MAC_OK")
