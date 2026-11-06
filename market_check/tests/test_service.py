import unittest
import pandas as pd
from backend.service import calculate_snapshot

class Calculations(unittest.TestCase):
    def test_periods_and_missing_ticker(self):
        idx = pd.date_range("2026-01-01", periods=6, freq="B")
        df = pd.DataFrame({("TEST", "Close"): [100, 105, 110, 120, 125, 150]}, index=idx)
        result = calculate_snapshot(df, {"Test": ["TEST", "MISSING"]})
        row = result.iloc[0]
        self.assertAlmostEqual(row["1D %"], 20)
        self.assertAlmostEqual(row["3D %"], (150/110-1)*100)
        self.assertAlmostEqual(row["5D %"], 50)
        self.assertEqual(result.iloc[1]["Stav"], "Chybí data")
    def test_short_history_and_gaps(self):
        df = pd.DataFrame({("TEST", "Close"): [100, None, 110]},
                          index=pd.date_range("2026-01-01", periods=3))
        row = calculate_snapshot(df, {"Test": ["TEST"]}).iloc[0]
        self.assertAlmostEqual(row["1D %"], 10)
        self.assertIsNone(row["5D %"])
        self.assertEqual(row["Stav"], "Krátká historie")

if __name__ == "__main__":
    unittest.main()
