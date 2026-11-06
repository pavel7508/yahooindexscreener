

# green yellow red circle
signal = ["\U0001F7E2", "\U0001F534", "\U0001F7E1", "\u26AA"]

index_income_stmt = ["Total Revenue", "Gross Profit", "Operating Income", "EBIT", "EBITDA", "Net Income", "Diluted EPS"]
index_margin = ["Gross Margin", "Operating Margin", "Net Margin"]

# sektorové a obobrové etf
sector_etfs = [
    "XLK",   # Technology
    "XLF",   # Financials
    "XLE",   # Energy
    "XLV",   # Health Care
    "XLI",   # Industrials
    "XLY",   # Consumer Discretionary
    "XLP",   # Consumer Staples
    "XLC",   # Communication Services
    "XLU",   # Utilities
    "XLB",   # Materials
    "XLRE",  # Real Estate
]

industry_etfs = [
    "SMH",   # Semiconductors
    "SOXX",  # Semiconductors
    "XRT",   # Retail
    "XHB",   # Homebuilders
    "XBI",   # Biotechnology
    "IBB",   # Biotechnology
    "KRE",   # Regional Banks
    "XOP",   # Oil & Gas Exploration
    "OIH",   # Oil Services
    "ITA",   # Aerospace & Defense
    "IGV",   # Software
    "HACK",  # Cybersecurity
]

#hlavní indexy
market_etfs = [
    "SPY",   # S&P 500
    "QQQ",   # Nasdaq 100
    "DIA",   # Dow Jones
    "IWM",   # Russell 2000
    "RSP",   # S&P 500 Equal Weight
]

market_indices = [
    "^GSPC",  # S&P 500
    "^NDX",   # Nasdaq 100
    "^DJI",   # Dow Jones
    "^RUT",   # Russell 2000
    "^SOX",   # Philadelphia Semiconductor Index
]

#makroekonomické ukazatele
macro_tickers = [
    "^VIX",       # VIX – volatilita
    "^TNX",       # US 10Y Treasury Yield
    "^TYX",       # US 30Y Treasury Yield
    "^FVX",       # US 5Y Treasury Yield
    "DX-Y.NYB",   # US Dollar Index (DXY)
    "JPY=X",      # USD/JPY
    "EURUSD=X",   # EUR/USD
    "CL=F",       # WTI Crude Oil
    "BZ=F",       # Brent Crude Oil
    "GC=F",       # Gold Futures
]

all_tickers = list(dict.fromkeys(
    sector_etfs
    + industry_etfs
    + market_etfs
    + market_indices
    + macro_tickers
))

