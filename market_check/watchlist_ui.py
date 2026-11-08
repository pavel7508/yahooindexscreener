"""Personal dashboard, with a per-browser watchlist and shared quote cache."""
from datetime import datetime
from html import escape
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from backend.catalog import load_catalog
from backend.watchlist import COLUMNS, MAX_ITEMS, clean_watchlist, download_quote, missing_row

_browser_store = components.declare_component(
    "marketcheck_browser_store", path=str(Path(__file__).parent / "components" / "browser_store")
)

_watch_table = components.declare_component(
    "marketcheck_watch_table", path=str(Path(__file__).parent / "components" / "watch_table")
)


@st.cache_data(ttl=3600, show_spinner=False)
def catalog_data():
    return load_catalog()


@st.cache_data(ttl=900, max_entries=2000, show_spinner=False)
def quote_data(provider_symbol):
    return download_quote(provider_symbol)


def render_table(frame, descriptions):
    left, right = st.columns([2, 1])
    column = left.selectbox("Řadit podle", ["Původní pořadí", *COLUMNS], key="watch_sort")
    direction = right.selectbox("Směr řazení", ["Vzestupně", "Sestupně"],
                                key="watch_direction", disabled=column == "Původní pořadí")
    if column != "Původní pořadí":
        frame = frame.sort_values(column, ascending=direction == "Vzestupně", na_position="last", kind="stable")

    def color(value):
        if pd.isna(value) or value == 0:
            return ""
        return "color: #4ade80" if value > 0 else "color: #fb7185"

    def ticker_html(value):
        label = escape(value, quote=True)
        return (
            f'<button type="button" class="remove-ticker" data-remove="{label}" '
            f'title="Odebrat {label}" aria-label="Odebrat {label}">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.8" aria-hidden="true">'
            '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>'
            '</svg></button>'
            f'<span title="{escape(descriptions.get(value, value), quote=True)}" style="cursor:help">{label}</span>'
        )

    styled = (frame.style.map(color, subset=["1D %", "3D %", "5D %"])
              .format({"Ticker": ticker_html, "Poslední cena": "{:.4f}",
                       **{f"{n}D %": "{:.2f} %" for n in (1, 3, 5)}}, escape="html", na_rep="")
              .hide(axis="index").set_table_attributes('class="market-table"'))
    event = _watch_table(
        html=TABLE_CSS + '<div class="market-table-scroll">' + styled.to_html() + '</div>',
        key="watch_table", default=None,
    )
    if isinstance(event, dict) and event.get("event_id") != st.session_state.get("watch_remove_event"):
        st.session_state.watch_remove_event = event.get("event_id")
        ticker = event.get("ticker")
        if ticker in st.session_state.watch_tickers:
            st.session_state.watch_tickers = [item for item in st.session_state.watch_tickers if item != ticker]
            st.session_state.get("watch_rows", {}).pop(ticker, None)
            st.rerun()


def render_watchlist():
    st.subheader("Vlastní přehled")
    stored = _browser_store(items=st.session_state.get("watch_tickers"), key="watch_browser_store", default=None)
    if "watch_tickers" not in st.session_state:
        if stored is None:
            st.info("Načítám seznam z prohlížeče…")
            return
        st.session_state.watch_tickers = clean_watchlist(stored.get("items"))
        st.rerun()
    if stored and stored.get("error"):
        st.warning(stored["error"])
    st.caption("Seznam se ukládá v tomto prohlížeči. Ceny mají cache 15 minut; katalog se obnovuje denně při používání aplikace.")
    try:
        with st.spinner("Načítám katalog instrumentů…"):
            items, updated, warning = catalog_data()
        if warning:
            st.warning(warning)
        st.caption(f"Katalog Nasdaq / NYSE: {datetime.fromtimestamp(updated):%d.%m.%Y %H:%M} · {len(items):,} instrumentů")
    except RuntimeError as exc:
        st.warning(str(exc))
        items = []
    if st.button("Obnovit katalog", key="watch_catalog_refresh"):
        catalog_data.clear()
        st.rerun()
    instruments = {item["ticker"]: item for item in items}
    tickers = st.session_state.watch_tickers
    choice = st.selectbox(
        "Vyhledej ticker nebo název společnosti", list(instruments), index=None,
        placeholder="Např. AAPL nebo Apple", key="watch_search",
        format_func=lambda ticker: f"{ticker} — {instruments[ticker]['name']} · {instruments[ticker]['exchange']}",
    )
    if st.button("Přidat", key="watch_add", disabled=choice is None or len(tickers) >= MAX_ITEMS):
        if choice in tickers:
            st.info("Tento ticker už v přehledu je.")
        else:
            st.session_state.watch_tickers = [*tickers, choice]
            st.rerun()
    if len(tickers) >= MAX_ITEMS:
        st.info(f"Přehled může obsahovat nejvýše {MAX_ITEMS} tickerů.")
    if not tickers:
        st.caption("Vyber instrument a klikni na Přidat.")
        st.divider()
        return

    if st.button("Aktualizovat vlastní přehled", key="watch_refresh"):
        for ticker in tickers:
            if ticker in instruments:
                quote_data.clear(instruments[ticker]["provider_symbol"])
    previous_rows = st.session_state.setdefault("watch_rows", {})
    rows = []
    with st.spinner("Načítám ceny vlastního přehledu…"):
        for ticker in tickers:
            instrument = instruments.get(ticker)
            if instrument is None:
                row = missing_row(ticker, "Ticker není v dostupném katalogu")
            else:
                row = dict(quote_data(instrument["provider_symbol"]))
                row["Ticker"] = ticker
            if pd.isna(row["Poslední cena"]) and ticker in previous_rows:
                row = {**previous_rows[ticker], "Stav": "Starší uložená data – " + row["Stav"]}
            elif not pd.isna(row["Poslední cena"]):
                previous_rows[ticker] = dict(row)
            rows.append(row)
    frame = pd.DataFrame(rows, columns=COLUMNS)
    for column in ("1D %", "3D %", "5D %", "Poslední cena"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    descriptions = {ticker: f"{item['name']} · {item['exchange']}" for ticker, item in instruments.items()}
    render_table(frame, descriptions)
    if (frame["Stav"] != "OK").any():
        st.warning("Některé instrumenty nemají úplná nebo aktuální data. Podrobnosti jsou ve sloupci Stav.")
    st.divider()


TABLE_CSS = """<style>
    .market-table-scroll {
        width: 100%; max-width: 100%; min-width: 0;
        box-sizing: border-box;
        max-height: 650px; overflow-x: auto; overflow-y: auto;
    }
    .remove-ticker {
        display: inline-flex; align-items: center; justify-content: center;
        vertical-align: middle; width: 28px; height: 28px; margin-right: 4px;
        padding: 0; border: 0; border-radius: 4px; cursor: pointer;
        color: inherit; background: transparent;
    }
    .remove-ticker:hover { color: #fb7185; background: #80808020; }
    .remove-ticker:focus-visible { outline: 2px solid var(--primary-color, #ff4b4b); }
    .market-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .market-table th, .market-table td {
        padding: 8px 12px; text-align: left; white-space: nowrap;
        border-bottom: 1px solid var(--border-color, #80808040);
    }
    .market-table thead th {
        position: sticky; top: 0;
        background: var(--background-color, #0e1117); z-index: 1;
    }
    @media (max-width: 768px) {
        /* Keep the table's intrinsic width inside its own scroll area. */
        .market-table-scroll {
            contain: inline-size;
            -webkit-overflow-scrolling: touch;
        }
        .market-table { width: max-content; min-width: 100%; }
        .market-table th, .market-table td { padding: 6px 4px; }
    }
    </style>"""
