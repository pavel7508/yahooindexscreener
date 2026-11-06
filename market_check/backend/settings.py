from configfrontend import sector_etfs, industry_etfs, market_etfs, market_indices, macro_tickers

GROUPS = {
    "Hlavní indexy": market_indices,
    "Tržní ETF": market_etfs,
    "Sektorová ETF": sector_etfs,
    "Oborová ETF": industry_etfs,
    "Makro": macro_tickers,
}
