"""ETF holdings from issuers. A missing/invalid source simply returns None."""
import csv
from io import BytesIO, StringIO
import re
from urllib.request import Request, urlopen
import pandas as pd
from configfrontend import sector_etfs

SPDR = set(sector_etfs) | {"XRT", "XHB", "XBI", "KRE", "XOP"}
ISHARES = {
    "SOXX": "239705/ishares-semiconductor-etf",
    "IBB": "239699/ishares-biotechnology-etf",
    "ITA": "239502/ishares-us-aerospace-defense-etf",
    "IGV": "239771/ishares-north-american-techsoftware-etf",
}


class HoldingsDependencyError(RuntimeError):
    """The source is available but the local Excel reader is missing."""


def source_url(ticker):
    if ticker in SPDR:
        return f"https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{ticker.lower()}.xlsx"
    if ticker in ISHARES:
        return f"https://www.ishares.com/us/products/{ISHARES[ticker]}/latest-holdings.csv"
    if ticker in {"SMH", "OIH"}:
        slug = "semiconductor-etf-smh" if ticker == "SMH" else "oil-services-etf-oih"
        return f"https://www.vaneck.com/us/en/investments/{slug}/downloads/holdings/"
    if ticker == "HACK":
        return "https://amplifyetfs.com/HACK-holdings/"
    return None


def normalize_holdings(frame):
    frame = frame.rename(columns={c: str(c).strip() for c in frame.columns})
    name = next((c for c in ("Name", "Holding Name", "Security Name") if c in frame), None)
    weight = next((c for c in ("Weight", "Weight (%)", "% of Net Assets", "Market Value (%)") if c in frame), None)
    if "Ticker" not in frame or not name or not weight:
        raise ValueError("Missing holdings columns")
    result = []
    for _, row in frame.iterrows():
        ticker = str(row["Ticker"]).strip()
        if not re.fullmatch(r"[A-Z]{1,6}(?:[.-][A-Z])?", ticker):
            continue
        if "Asset Class" in frame and str(row["Asset Class"]).strip() != "Equity":
            continue
        value = pd.to_numeric(str(row[weight]).replace("%", "").replace(",", "").strip(), errors="coerce")
        if pd.isna(value) or not 0 < value <= 100 or pd.isna(row[name]):
            continue
        result.append({"Ticker": ticker, "Název": str(row[name]), "Váha v ETF %": float(value)})
    if not result:
        raise ValueError("Empty holdings")
    return (pd.DataFrame(result).drop_duplicates("Ticker")
            .sort_values("Váha v ETF %", ascending=False, kind="stable").head(25).to_dict("records"))


def parse_holdings(data, kind):
    metadata = ""
    if kind == "csv":
        lines = data.decode("utf-8-sig").splitlines()
        header = next(i for i, line in enumerate(lines) if line.startswith("Ticker,"))
        metadata = " ".join(lines[:header])
        frame = pd.DataFrame(list(csv.DictReader(StringIO("\n".join(lines[header:])))))
    elif kind == "xlsx":
        try:
            raw = pd.read_excel(BytesIO(data), header=None, engine="openpyxl")
        except ImportError as exc:
            raise HoldingsDependencyError(
                "Pro načtení složení tohoto ETF chybí nebo nevyhovuje knihovna openpyxl. "
                "Aktualizuj závislosti v prostředí, ve kterém běží aplikace, a aplikaci restartuj."
            ) from exc
        header = next(i for i, row in raw.iterrows() if "Ticker" in row.astype(str).str.strip().tolist())
        metadata = " ".join(raw.iloc[:header].fillna("").astype(str).values.flatten())
        frame = raw.iloc[header + 1:].copy()
        frame.columns = raw.iloc[header].tolist()
    else:
        tables = pd.read_html(StringIO(data.decode("utf-8")), flavor="lxml")
        frame = next(table for table in tables if "Ticker" in table.columns)
    date_match = re.search(r"\b(?:\d{1,2}-[A-Za-z]{3}-\d{4}|[A-Za-z]{3,9} \d{1,2}, \d{4}|\d{1,2}/\d{1,2}/\d{4})\b", metadata)
    as_of = date_match.group(0) if date_match else None
    return {"rows": normalize_holdings(frame), "as_of": as_of}


def load_holdings(ticker, fetch=None):
    url = source_url(ticker)
    if url is None:
        return None
    try:
        if fetch is None:
            with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 MarketCheck/1.1"}), timeout=15) as response:
                data = response.read(5_000_001)
        else:
            data = fetch(url)
        if len(data) > 5_000_000:
            return None
        kind = "xlsx" if ticker in SPDR or ticker in {"SMH", "OIH"} else "csv" if ticker in ISHARES else "html"
        result = parse_holdings(data, kind)
        result["source"] = url
        return result
    except HoldingsDependencyError:
        raise
    except Exception:
        return None
