from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from backend.service import load_snapshot, update_snapshot
from backend.settings import GROUPS

st.set_page_config(page_title="Market Check", page_icon="📊", layout="wide")
st.title("Market Check")
st.caption("Rychlý přehled indexů, sektorů a makra · Yahoo Finance")
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

selected = st.sidebar.multiselect("Zobrazit skupiny", list(GROUPS), default=list(GROUPS))
st.sidebar.caption("Při otevření ani změně filtru se nic nestahuje.")
if snapshot is None:
    st.info("Pro první načtení klikni na Aktualizovat data.")
    st.stop()

table, updated = snapshot
stamp = datetime.fromisoformat(updated).astimezone(ZoneInfo("Europe/Prague"))
st.caption(f"Poslední stažení: {stamp:%d.%m.%Y %H:%M %Z}")
st.caption("Cena = poslední dostupné denní Close. Během seance může být průběžná. "
           "Změna = (poslední Close / Close před N obchodními svíčkami − 1) × 100. "
           "Jde o cenovou změnu bez dividendové úpravy; 5D není kalendářní týden.")
shown = table[table["Skupina"].isin(selected)].copy()
for col in ("Poslední cena", "1D %", "3D %", "5D %"):
    shown[col] = pd.to_numeric(shown[col], errors="coerce")

def color_change(value):
    if pd.isna(value) or value == 0:
        return ""
    return "color: #4ade80" if value > 0 else "color: #fb7185"

styled = shown.style.map(color_change, subset=["1D %", "3D %", "5D %"])
st.dataframe(styled, hide_index=True, use_container_width=True, height=650,
    column_config={
        "Poslední cena": st.column_config.NumberColumn(format="%.4f"),
        **{f"{n}D %": st.column_config.NumberColumn(format="%.2f %%") for n in (1, 3, 5)},
    })
if (shown["Stav"] != "OK").any():
    st.warning("Některá data chybí nebo jsou starší. Zkontroluj sloupce Datum dat a Stav.")
st.caption("Výnosy dluhopisů jsou hodnoty Yahoo; jejich změny zde znamenají relativní %, nikoli bazické body. "
           "Jednotky se mezi ETF, indexy, měnami a komoditami liší.")
