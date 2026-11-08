from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from backend.service import load_snapshot, update_snapshot
from backend.settings import GROUPS
from configfrontend import etf_descriptions, group_display_names
from watchlist_ui import render_watchlist

st.set_page_config(page_title="Market Check", page_icon="📊", layout="wide")
st.title("Market Check")
st.caption("Rychlý přehled indexů, sektorů a makra · Yahoo Finance")
render_watchlist()
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
    label = escape(str(ticker))
    description = etf_descriptions.get(ticker)
    if description is None:
        return label
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
st.html(
    """<style>
    .market-table-scroll {
        width: 100%; max-width: 100%; min-width: 0;
        box-sizing: border-box;
        max-height: 650px; overflow-x: auto; overflow-y: auto;
    }
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
    + '<div class="market-table-scroll">' + styled.to_html() + '</div>'
)
if (shown["Stav"] != "OK").any():
    st.warning("Některá data chybí nebo jsou starší. Zkontroluj sloupce Datum dat a Stav.")
st.caption("Výnosy dluhopisů jsou hodnoty Yahoo; jejich změny zde znamenají relativní %, nikoli bazické body. "
           "Jednotky se mezi ETF, indexy, měnami a komoditami liší.")
