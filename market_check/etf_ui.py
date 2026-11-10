"""One ETF detail panel, selected by clicking a sector/industry ticker."""
from concurrent.futures import ThreadPoolExecutor
from html import escape
import pandas as pd
import streamlit as st
from backend.holdings import load_holdings, HoldingsDependencyError
from backend.watchlist import COLUMNS, MAX_ITEMS
from watchlist_ui import _watch_table, TABLE_CSS, catalog_data, quote_data


class HoldingsUnavailable(RuntimeError):
    pass


@st.cache_data(ttl=86400, max_entries=32, show_spinner=False)
def holdings_data(ticker):
    result = load_holdings(ticker)
    # Streamlit caches return values, but does not cache exceptions.
    # A temporary failure must not hide an ETF for the next 24 hours.
    if result is None:
        raise HoldingsUnavailable()
    return result


def render_etf_detail():
    ticker = st.session_state.get("selected_etf")
    if not ticker:
        return
    st.subheader(f"{ticker} · Top 25 pozic", anchor="etf-holdings-detail")
    if st.button("Zavřít detail", key="close_etf_detail"):
        st.session_state.selected_etf = None
        st.rerun()
    try:
        with st.spinner(f"Načítám složení {ticker}…"):
            holdings = holdings_data(ticker)
    except HoldingsDependencyError as exc:
        st.error(str(exc))
        st.code("python -m pip install -r market_check/requirements.txt", language="bash")
        st.caption("Příkaz spusť z hlavní složky projektu v prostředí aplikace.")
        return
    except HoldingsUnavailable:
        st.info("Složení ETF není dostupné.")
        return
    positions = holdings["rows"]
    covered = sum(row["Váha v ETF %"] for row in positions)
    as_of = holdings["as_of"] or "neuvedeno"
    st.caption(f"{len(positions)} největších akciových pozic · váha celkem {covered:.2f} % · datum složení: {as_of}")
    st.markdown(f"[Zdroj složení]({holdings['source']})")
    try:
        instruments = {item["ticker"]: item for item in catalog_data()[0]}
    except RuntimeError:
        instruments = {}
    watchlist = st.session_state.get("watch_tickers", [])
    can_add = "watch_tickers" in st.session_state and len(watchlist) < MAX_ITEMS

    def price(position):
        symbol = position["Ticker"]
        provider = instruments.get(symbol, {}).get("provider_symbol", symbol.replace(".", "-"))
        return {**quote_data(provider), **position}

    with st.spinner("Načítám performance pozic…"):
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(price, positions))
    columns = ["Ticker", "Váha v ETF %", *COLUMNS[1:]]
    frame = pd.DataFrame(rows)[columns]
    for column in ("Váha v ETF %", "1D %", "3D %", "5D %", "Poslední cena"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    left, right = st.columns([2, 1])
    sort = left.selectbox("Řadit pozice podle", columns, index=1, key=f"etf_sort_{ticker}")
    direction = right.selectbox("Směr řazení pozic", ["Sestupně", "Vzestupně"], key=f"etf_direction_{ticker}")
    frame = frame.sort_values(sort, ascending=direction == "Vzestupně", na_position="last", kind="stable")
    names = {position["Ticker"]: position["Název"] for position in positions}

    def ticker_html(value):
        label = escape(value, quote=True)
        if value in watchlist:
            action = '<span title="Již ve watchlistu" aria-label="Již ve watchlistu">✓</span> '
        elif value in instruments and can_add:
            action = (f'<button type="button" class="remove-ticker" data-add="{label}" '
                      f'title="Přidat {label} do watchlistu" aria-label="Přidat {label} do watchlistu">＋</button>')
        else:
            action = '<span title="Přidání nyní není dostupné">—</span> '
        return action + f'<span title="{escape(names[value], quote=True)}">{label}</span>'

    def color(value):
        if pd.isna(value) or value == 0:
            return ""
        return "color: #4ade80" if value > 0 else "color: #fb7185"

    styled = (frame.style.map(color, subset=["1D %", "3D %", "5D %"])
              .format({"Ticker": ticker_html, "Váha v ETF %": "{:.2f} %", "Poslední cena": "{:.4f}",
                       **{f"{n}D %": "{:.2f} %" for n in (1, 3, 5)}}, escape="html", na_rep="")
              .hide(axis="index").set_table_attributes('class="market-table"'))
    event = _watch_table(html=TABLE_CSS + '<div class="market-table-scroll">' + styled.to_html() + '</div>',
                         key="etf_detail_table", default=None)
    if (isinstance(event, dict) and event.get("event_id") != st.session_state.get("etf_add_event")):
        st.session_state.etf_add_event = event.get("event_id")
        symbol = event.get("ticker")
        if (event.get("action") == "add" and symbol in names and symbol in instruments
                and symbol not in watchlist and can_add):
            st.session_state.watch_tickers = [*watchlist, symbol]
            st.rerun()
    if not can_add:
        st.caption("Přidání do watchlistu není nyní dostupné (načítání seznamu nebo dosažený limit).")
    if (frame["Stav"] != "OK").any():
        st.caption("Některé ceny nejsou dostupné nebo aktuální; podrobnosti jsou ve sloupci Stav.")
