"""Watchlist validation and prices; reuse the main dashboard calculations."""
import re
import pandas as pd
from backend.service import calculate_snapshot

MAX_ITEMS = 100
COLUMNS = ["Ticker", "1D %", "3D %", "5D %", "Poslední cena", "Datum dat", "Stav"]


def clean_watchlist(value):
    if not isinstance(value, list):
        return []
    result = []
    seen = set()
    for ticker in value:
        if (isinstance(ticker, str) and re.fullmatch(r"[A-Z]{1,6}(?:[.-][A-Z])?", ticker)
                and ticker not in seen):
            result.append(ticker)
            seen.add(ticker)
        if len(result) >= MAX_ITEMS:
            break
    return result


def missing_row(ticker, status):
    return {**dict.fromkeys(COLUMNS), "Ticker": ticker, "Stav": status}


def download_quote(provider_symbol, downloader=None):
    if downloader is None:
        import yfinance as yf
        downloader = yf.download
    try:
        history = downloader(provider_symbol, period="1mo", interval="1d", group_by="ticker",
                             auto_adjust=False, threads=False, progress=False, timeout=15)
        if history is None or history.empty:
            return missing_row(provider_symbol, "Chybí data")
        row = calculate_snapshot(history, {"Watchlist": [provider_symbol]}).iloc[0].to_dict()
        row.pop("Skupina", None)
        if row.get("Datum dat") and (pd.Timestamp.now().normalize() - pd.Timestamp(row["Datum dat"])).days > 7:
            row["Stav"] = "Starší data"
        return row
    except Exception:
        return missing_row(provider_symbol, "Data nedostupná – zkus aktualizovat později")
