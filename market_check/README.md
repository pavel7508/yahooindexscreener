# Market Check
Samostatný Python projekt pro rychlý přehled instrumentů ze zaslaného configfrontend.py.
Původní GitHub screener se nemění. Obsahuje všech 43 tickerů v pěti skupinách.

## Spuštění (Windows / PyCharm terminál)
Z hlavní složky projektu:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Při dalších spuštěních s aktivním prostředím stačí poslední příkaz nebo run_windows.bat.
Na Linuxu/macOS aktivuj prostředí příkazem `source .venv/bin/activate`.

## Ovládání
První stažení spustí tlačítko **Aktualizovat data**. Potom se automaticky načítá
`data/snapshot.json`; otevření aplikace, řazení a filtrování nespouští download.
Pro samostatný download nebo Plánovač úloh použij `python main.py`.
Neprováděj současně více aktualizací stejného souboru.

## Struktura
- app.py: Streamlit frontend, skupiny a barevné procentní změny.
- configfrontend.py: seznamy ze zaslaného souboru (odstraněn pouze výpis při importu).
- backend/settings.py: přiřazení skupin.
- backend/service.py: Yahoo download, výpočty a uložení snapshotu.
- main.py: samostatný aktualizační příkaz.
- data/: automaticky vytvořená uložená data.
- .streamlit/config.toml: tmavý motiv.
- tests/test_service.py: kontrola výpočtů a chybějící historie.

## Výpočty a význam cen
Poslední cena je neadjustovaný Close z poslední dostupné denní svíčky Yahoo.
Během otevřeného trhu může tato svíčka obsahovat průběžnou cenu; nejde o garantovanou
živou kotaci ani pouze o dokončené seance. Datum je uvedeno pro každý instrument.
1D, 3D a 5D používají posledních 1, 3 a 5 dostupných obchodních intervalů:
`(Close[-1] / Close[-N-1] - 1) * 100`.
Pro 5D je potřeba alespoň šest cen. Svátky a víkendy se nepočítají.
Chybějící hodnoty se zobrazí prázdné. Při částečném výpadku zůstane starší uložený
řádek označený ve sloupci Stav. Při celkovém výpadku zůstane původní soubor.
Čas aktualizace označuje stažení, nikoli čas posledního obchodu.

Procenta nejsou celkový výnos s dividendami. U dluhopisových výnosů jde o relativní
procentní změnu, nikoli změnu v bazických bodech. Různé instrumenty mají různé jednotky.
Data poskytuje Yahoo prostřednictvím neoficiální knihovny yfinance a mohou mít zpoždění.

## Testy
`python -m unittest discover -s tests -v`

## Vlastní přehled (1.1)

Nad přehledem trhu je vyhledávání podle tickeru i názvu společnosti. Vyber výsledek
z nabídky a potvrď **Přidat**. Vlastní tabulka ukazuje 1D, 3D a 5D změny podle stejného
výpočtu jako hlavní přehled. Řádky lze řadit a jednotlivé tickery odebrat ikonou koše vedle tickeru.

Seznam až 100 tickerů se ukládá do `localStorage` prohlížeče pomocí lokální Streamlit
komponenty. Na jiném zařízení/prohlížeči je seznam samostatný; smazání dat webu ho
odstraní. Při zakázaném úložišti zůstává seznam pouze v aktuální relaci a aplikace
zobrazí upozornění. Seznam uživatele se neukládá do společného souboru na serveru.

Katalog Nasdaq a NYSE (včetně NYSE Arca a American) pochází z oficiálních souborů
[Nasdaq Trader](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs).
Obnovuje se při používání aplikace po 24 hodinách. Kontrola diskové cache běží
nejvýše jednou za hodinu; tlačítko **Obnovit katalog** tuto kontrolu zopakuje ihned.
Při výpadku zdroje se použije předchozí katalog a zobrazí se upozornění.
Disková cache je `data/instruments.json` a není určena ke commitování.

Katalog rozlišuje `ticker`, `name`, `exchange` a `provider_symbol`. Třídy akcií jako
`BRK.B` mají pro Yahoo symbol `BRK-B`. Testovací instrumenty a složité suffixy
preferenčních akcií či jednotek, pro které nemáme spolehlivé mapování, se nenabízejí.
Platný výběr z katalogu nezaručuje dostupnost cen u Yahoo.

Ceny mají sdílenou paměťovou cache 15 minut pro každý symbol. Tlačítko
**Aktualizovat vlastní přehled** vyprázdní cache pouze vybraných instrumentů.
Neúspěšná načtení mají stav ve sloupci Stav; pokud v relaci existuje starší úspěšná
hodnota, zůstane viditelná a jasně označená. Ticker vyřazený z katalogu se ze seznamu
sám nesmaže. Pro funkci je potřebný přístup k Nasdaq Trader a Yahoo Finance.
