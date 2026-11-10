from io import BytesIO
import unittest
import pandas as pd
from backend.holdings import load_holdings, normalize_holdings, parse_holdings, HoldingsDependencyError
from unittest.mock import patch

class HoldingsTests(unittest.TestCase):
    def test_csv_date_filter_and_sort(self):
        data=b'Fund Holdings as of,"Nov 06, 2026"\nTicker,Name,Asset Class,Weight (%)\nAAPL,Apple,Equity,12.5\nMSFT,Microsoft,Equity,20\nUSD,Cash,Cash,50\n'
        result=parse_holdings(data,"csv")
        self.assertEqual(result["as_of"],"Nov 06, 2026")
        self.assertEqual([r["Ticker"] for r in result["rows"]],["MSFT","AAPL"])
        self.assertEqual(result["rows"][0]["Váha v ETF %"],20)

    def test_xlsx_header_offset(self):
        data=BytesIO()
        pd.DataFrame([["Holdings:","As of 06-Nov-2026"],["Name","Ticker","Weight"],["Apple","AAPL",15.2]]).to_excel(data,index=False,header=False)
        result=parse_holdings(data.getvalue(),"xlsx")
        self.assertEqual(result["as_of"],"06-Nov-2026")
        self.assertEqual(result["rows"][0]["Ticker"],"AAPL")

    def test_top25_without_reweighting(self):
        frame=pd.DataFrame([{"Ticker":"T"+chr(65+i),"Name":"Test","Weight":i+1} for i in range(26)])
        rows=normalize_holdings(frame)
        self.assertEqual(len(rows),25)
        self.assertEqual(rows[0]["Váha v ETF %"],26)
        self.assertEqual(rows[-1]["Váha v ETF %"],2)

    def test_unavailable(self):
        def fail(url):raise OSError("offline")
        self.assertIsNone(load_holdings("XLK",fail))
        self.assertIsNone(load_holdings("SOXX",lambda url:b"<html>Unavailable</html>"))
        self.assertIsNone(load_holdings("UNKNOWN",fail))

    def test_missing_excel_dependency_is_not_hidden_as_source_failure(self):
        with patch("backend.holdings.pd.read_excel", side_effect=ImportError("openpyxl missing")):
            with self.assertRaises(HoldingsDependencyError):
                load_holdings("XLK", lambda url: b"excel data")

    def test_failed_download_is_retried_but_success_is_cached(self):
        from etf_ui import holdings_data, HoldingsUnavailable
        payload = {"rows": [{"Ticker": "AAPL"}], "as_of": "06-Nov-2026"}
        holdings_data.clear()
        try:
            with patch("etf_ui.load_holdings", side_effect=[None, payload]) as fetch:
                with self.assertRaises(HoldingsUnavailable):
                    holdings_data("XLK")
                self.assertEqual(holdings_data("XLK"), payload)
                self.assertEqual(holdings_data("XLK"), payload)
                self.assertEqual(fetch.call_count, 2)
        finally:
            holdings_data.clear()
