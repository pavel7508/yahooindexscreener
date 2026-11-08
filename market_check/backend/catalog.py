"""Nasdaq Trader instrument directory with a daily, atomic disk cache."""
import csv
import io
import json
import re
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen

CACHE = Path(__file__).resolve().parents[1] / "data" / "instruments.json"
SOURCES = {
    "nasdaq": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "other": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
EXCHANGES = {"N": "NYSE", "P": "NYSE Arca", "A": "NYSE American"}


def parse_directory(text, source):
    reader = csv.DictReader(io.StringIO(text), delimiter="|")
    required = {"Security Name", "Test Issue", "Symbol" if source == "nasdaq" else "ACT Symbol"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Neplatný formát katalogu Nasdaq Trader.")
    result = []
    for row in reader:
        if row.get("Test Issue") != "N":
            continue
        exchange = "NASDAQ" if source == "nasdaq" else EXCHANGES.get(row.get("Exchange"))
        symbol = row.get("Symbol" if source == "nasdaq" else "ACT Symbol", "")
        name = row.get("Security Name", "")
        # Include ordinary shares, share classes and ETFs. Exotic preferred/unit
        # suffixes need a provider-specific mapping and are not guessed here.
        if not exchange or not name or not re.fullmatch(r"[A-Z]{1,6}(?:[.-][A-Z])?", symbol):
            continue
        result.append({"ticker": symbol, "name": name, "exchange": exchange,
                       "provider_symbol": symbol.replace(".", "-")})
    if not result:
        raise ValueError("Katalog Nasdaq Trader neobsahuje použitelné instrumenty.")
    return result


def load_catalog(cache_path=CACHE, fetch=None, now=None):
    now = time.time() if now is None else now
    previous = None
    try:
        previous = json.loads(cache_path.read_text(encoding="utf-8"))
        if (not isinstance(previous, dict) or not isinstance(previous.get("items"), list)
                or not previous["items"] or not all(
                    isinstance(item, dict) and all(isinstance(item.get(field), str) and item[field]
                        for field in ("ticker", "name", "exchange", "provider_symbol"))
                    for item in previous["items"])):
            raise ValueError("Invalid catalog")
        if now - float(previous["updated_at"]) < 86400:
            return previous["items"], previous["updated_at"], None
    except (OSError, ValueError, KeyError, TypeError):
        previous = None

    def download(url):
        request = Request(url, headers={"User-Agent": "MarketCheck/1.1"})
        with urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8-sig")

    try:
        items = {}
        for source, url in SOURCES.items():
            for item in parse_directory((fetch or download)(url), source):
                items[item["ticker"]] = item
        payload = {"updated_at": now, "items": sorted(items.values(), key=lambda item: item["ticker"])}
    except Exception as exc:
        if previous:
            return previous["items"], previous["updated_at"], f"Katalog se nepodařilo obnovit; používám uloženou verzi. {exc}"
        raise RuntimeError("Katalog instrumentů není dostupný. Zkus načtení později.") from exc

    warning = None
    temporary = None
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=cache_path.parent,
                                suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False)
        temporary.replace(cache_path)
    except OSError:
        warning = "Katalog byl načten, ale jeho diskovou cache nelze uložit."
    finally:
        if temporary and temporary.exists():
            temporary.unlink(missing_ok=True)
    return payload["items"], now, warning
