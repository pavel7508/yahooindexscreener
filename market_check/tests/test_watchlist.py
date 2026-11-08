import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import pandas as pd
from backend.catalog import load_catalog, parse_directory
from backend.watchlist import clean_watchlist, download_quote

NASDAQ = "Symbol|Security Name|Test Issue\nAAPL|Apple Inc.|N\nTEST|Test issue|Y\nFile Creation Time: yesterday||\n"
NYSE = "ACT Symbol|Security Name|Exchange|Test Issue\nBRK.B|Berkshire Hathaway Class B|N|N\nSPY|SPDR S&P 500|P|N\nOTHER|Other exchange|Z|N\n"


class CatalogTests(unittest.TestCase):
    def test_filter_and_provider_mapping(self):
        self.assertEqual([r["ticker"] for r in parse_directory(NASDAQ, "nasdaq")], ["AAPL"])
        rows = parse_directory(NYSE, "other")
        self.assertEqual([r["ticker"] for r in rows], ["BRK.B", "SPY"])
        self.assertEqual(rows[0]["provider_symbol"], "BRK-B")

    def test_daily_refresh_and_failed_refresh_keeps_old_catalog(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return NASDAQ if "nasdaqlisted" in url else NYSE
        with TemporaryDirectory() as folder:
            cache = Path(folder) / "catalog.json"
            first = load_catalog(cache, fetch, now=100000)
            self.assertEqual(len(calls), 2)
            cached = load_catalog(cache, fetch, now=100100)
            self.assertEqual(cached, first)
            self.assertEqual(len(calls), 2)
            def fail(url):
                raise OSError("offline")
            stale = load_catalog(cache, fail, now=200000)
            self.assertEqual(stale[:2], first[:2])
            self.assertIsNotNone(stale[2])
            self.assertEqual(json.loads(cache.read_text(encoding="utf-8"))["updated_at"], 100000)
            load_catalog(cache, fetch, now=200000)
            self.assertEqual(len(calls), 4)

    def test_invalid_payload_does_not_replace_cache(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                load_catalog(Path(folder)/"catalog.json", lambda url: "<html>Unavailable</html>", now=100000)


class WatchlistTests(unittest.TestCase):
    def test_browser_input_validation_and_duplicates(self):
        self.assertEqual(clean_watchlist(["AAPL", "AAPL", "BRK.B", "<script>", None, 1]), ["AAPL", "BRK.B"])
        self.assertEqual(clean_watchlist({"ticker": "AAPL"}), [])

    def test_price_periods_reuse_main_calculation(self):
        history = pd.DataFrame({"Close": [100, 105, 110, 120, 125, 150]},
                               index=pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=6))
        row = download_quote("BRK-B", lambda *args, **kwargs: history)
        self.assertEqual(row["Ticker"], "BRK-B")
        self.assertAlmostEqual(row["1D %"], 20)
        self.assertAlmostEqual(row["3D %"], (150/110-1)*100)
        self.assertAlmostEqual(row["5D %"], 50)
        self.assertEqual(row["Stav"], "OK")

    def test_empty_and_failed_prices(self):
        self.assertIsNone(download_quote("AAPL", lambda *a, **kw: pd.DataFrame())["Poslední cena"])
        def fail(*args, **kwargs):
            raise TimeoutError("offline")
        row = download_quote("AAPL", fail)
        self.assertIsNone(row["Poslední cena"])
        self.assertNotEqual(row["Stav"], "OK")

    def test_short_history_and_old_data(self):
        history = pd.DataFrame({"Close": [10, 11]}, index=pd.date_range("2020-01-01", periods=2))
        row = download_quote("OLD", lambda *a, **kw: history)
        self.assertIsNone(row["5D %"])
        self.assertNotEqual(row["Stav"], "OK")


if __name__ == "__main__":
    unittest.main()
