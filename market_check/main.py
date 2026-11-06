"""Samostatná aktualizace: python main.py (lze spouštět plánovačem)."""
from backend.service import update_snapshot
from backend.settings import GROUPS

if __name__ == "__main__":
    table, updated = update_snapshot(GROUPS)
    print(f"Aktualizováno {updated}: {len(table)} instrumentů")
    print(table[["Ticker", "Stav"]].to_string(index=False))
