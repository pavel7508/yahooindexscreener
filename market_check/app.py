from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from backend.service import load_snapshot, update_snapshot
from backend.settings import GROUPS
from configfrontend import etf_descriptions, group_display_names, ticker_display_names
from watchlist_ui import render_watchlist, _watch_table, TABLE_CSS
from etf_ui import render_etf_detail
from configfrontend import sector_etfs, industry_etfs

st.set_page_config(page_title="Market Check", page_icon="📊", layout="wide")
st.title("Market Check")
st.caption("Rychlý přehled indexů, sektorů a makra · Yahoo Finance")
render_watchlist()
# Keep the market iframe in a stable layout during the browser-store handshake.
if "watch_tickers" not in st.session_state:
    st.stop()
st.subheader("Přehled trhu")
try:
    snapshot = load_snapshot()
except (ValueError, OSError, KeyError) as exc:
    snapshot = None
    st.warning(f"Uložená data nelze načíst: {exc}")

if st.sidebar.button("Aktualizovat data", type="primary", use_container_width=True):
    try:
        with st.spinner("Stahuji data z Yahoo…"):
            snapshot = update_snapshot(GROUPS)
        st.sidebar.success("Aktualizace dokončena")
    except Exception as exc:
        st.error(f"Aktualizace se nezdařila: {exc}")

selected = st.sidebar.multiselect(
    "Zobrazit skupiny", list(GROUPS), default=list(GROUPS),
    format_func=lambda group: group_display_names.get(group, group),
)
st.sidebar.caption("Přehled trhu používá uložená data; změna filtru nic nestahuje.")
if snapshot is None:
    st.info("Pro první načtení klikni na Aktualizovat data.")
    st.stop()

table, updated = snapshot
stamp = datetime.fromisoformat(updated).astimezone(ZoneInfo("Europe/Prague"))
st.caption(f"Poslední stažení: {stamp:%d.%m.%Y %H:%M %Z}")
st.caption("Cena = poslední dostupné denní Close. Během seance může být průběžná. "
           "Změna = (poslední Close / Close před N obchodními svíčkami − 1) × 100. "
           "Jde o cenovou změnu bez dividendové úpravy; 5D není kalendářní týden.")
shown = table.loc[
    table["Skupina"].isin(selected),
    ["Skupina", "Ticker", "1D %", "3D %", "5D %", "Poslední cena", "Datum dat", "Stav"],
].copy()
shown["Skupina"] = shown["Skupina"].replace(group_display_names)
for col in ("Poslední cena", "1D %", "3D %", "5D %"):
    shown[col] = pd.to_numeric(shown[col], errors="coerce")


sort_column_control, sort_direction_control = st.columns([2, 1])
with sort_column_control:
    sort_column = st.selectbox(
        "Řadit podle", ["Původní pořadí", *shown.columns], key="sort_column"
    )
with sort_direction_control:
    sort_direction = st.selectbox(
        "Směr řazení", ["Vzestupně", "Sestupně"],
        key="sort_direction", disabled=sort_column == "Původní pořadí",
    )
if sort_column != "Původní pořadí":
    shown = shown.sort_values(
        sort_column, ascending=sort_direction == "Vzestupně",
        na_position="last", kind="stable",
    )

def color_change(value):
    if pd.isna(value) or value == 0:
        return ""
    return "color: #4ade80" if value > 0 else "color: #fb7185"

def ticker_with_tooltip(ticker):
    if ticker in ticker_display_names:
        title = escape(f"{ticker} · {etf_descriptions.get(ticker, '')}", quote=True)
        return f'<span title="{title}" style="cursor: help">{escape(ticker_display_names[ticker])}</span>'
    label = escape(str(ticker))
    description = etf_descriptions.get(ticker)
    if description is None:
        return label
    if ticker in sector_etfs or ticker in industry_etfs:
        return (f'<button type="button" data-open="{label}" title="{escape(description, quote=True)}" '
                f'aria-label="Zobrazit složení {label}" style="font:inherit;color:inherit;cursor:pointer;'
                f'background:none;border:0;padding:0;text-decoration:underline">{label}</button>')
    return f'<span title="{escape(description, quote=True)}" style="cursor: help">{label}</span>'


# st.dataframe does not render per-cell HTML tooltips.
# Escape table values before inserting the trusted tooltip markup.
styled = (
    shown.style
    .map(color_change, subset=["1D %", "3D %", "5D %"])
    .format({"Ticker": ticker_with_tooltip,
             "Poslední cena": "{:.4f}",
             **{f"{n}D %": "{:.2f} %" for n in (1, 3, 5)}}, escape="html", na_rep="")
    .hide(axis="index")
    .set_table_attributes('class="market-table"')
)
event = _watch_table(
    html=TABLE_CSS + '<div class="market-table-scroll">' + styled.to_html() + '</div>',
    key="market_table", default=None,
    scroll_to=({"anchor": "etf-holdings-detail", "token": st.session_state.get("etf_scroll_request")}
               if st.session_state.get("selected_etf") and st.session_state.get("etf_scroll_request") else None),
)
if isinstance(event, dict) and event.get("event_id") != st.session_state.get("market_open_event"):
    st.session_state.market_open_event = event.get("event_id")
    if event.get("action") == "open" and event.get("ticker") in sector_etfs + industry_etfs:
        st.session_state.selected_etf = event["ticker"]
        st.session_state.etf_scroll_request = event["event_id"] if event.get("mobile") else None
        st.rerun()
render_etf_detail()
if (shown["Stav"] != "OK").any():
    st.warning("Některá data chybí nebo jsou starší. Zkontroluj sloupce Datum dat a Stav.")
st.caption("Výnosy dluhopisů jsou hodnoty Yahoo; jejich změny zde znamenají relativní %, nikoli bazické body. "
           "Jednotky se mezi ETF, indexy, měnami a komoditami liší.")
