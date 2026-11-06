"""Stažení, lokální cache a výpočet změn. Import nestahuje data."""
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "snapshot.json"


def calculate_snapshot(history, groups):
    rows = []
    for group, tickers in groups.items():
        for ticker in tickers:
            close = pd.Series(dtype=float)
            if isinstance(history.columns, pd.MultiIndex):
                if ticker in history.columns.get_level_values(0):
                    frame = history[ticker]
                    if "Close" in frame:
                        close = frame["Close"]
            elif len(set(t for ts in groups.values() for t in ts)) == 1 and "Close" in history:
                close = history["Close"]
            close = pd.to_numeric(close, errors="coerce").dropna().sort_index()
            close = close[~close.index.duplicated(keep="last")]
            row = {"Skupina": group, "Ticker": ticker, "Datum dat": None,
                   "Poslední cena": None, "1D %": None, "3D %": None, "5D %": None,
                   "Stav": "Chybí data"}
            if not close.empty:
                row.update({"Datum dat": str(close.index[-1].date()),
                            "Poslední cena": float(close.iloc[-1]), "Stav": "OK"})
                for days in (1, 3, 5):
                    if len(close) > days and close.iloc[-days-1] != 0:
                        row[f"{days}D %"] = float((close.iloc[-1] / close.iloc[-days-1] - 1) * 100)
                    else:
                        row["Stav"] = "Krátká historie"
            rows.append(row)
    return pd.DataFrame(rows)


def load_snapshot():
    if not CACHE.exists():
        return None
    payload = json.loads(CACHE.read_text(encoding="utf-8"))
    return pd.DataFrame(payload["rows"]), payload["updated_at"]


def update_snapshot(groups):
    import yfinance as yf
    tickers = list(dict.fromkeys(t for ts in groups.values() for t in ts))
    history = yf.download(tickers, period="1mo", interval="1d", group_by="ticker",
                          auto_adjust=False, threads=5, progress=False, timeout=20)
    if history is None or history.empty:
        raise RuntimeError("Yahoo nevrátilo data. Předchozí uložená data zůstala zachována.")
    table = calculate_snapshot(history, groups)
    if table["Poslední cena"].notna().sum() == 0:
        raise RuntimeError("Yahoo nevrátilo použitelné ceny.")
    # Při částečném výpadku ponecháme předchozí řádky a jasně je označíme.
    previous = load_snapshot()
    if previous:
        old = previous[0].set_index("Ticker")
        for i, row in table.iterrows():
            if pd.isna(row["Poslední cena"]) and row["Ticker"] in old.index:
                prior = old.loc[row["Ticker"]]
                if isinstance(prior, pd.DataFrame):
                    prior = prior.iloc[0]
                for col in ("Datum dat", "Poslední cena", "1D %", "3D %", "5D %"):
                    table.at[i, col] = prior[col]
                table.at[i, "Stav"] = "Starší uložená data – výpadek Yahoo"
    updated = datetime.now(timezone.utc).isoformat()
    payload = {"updated_at": updated, "rows": json.loads(table.to_json(orient="records"))}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(CACHE)
    return table, updated
