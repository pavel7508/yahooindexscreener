# Market Index Screener 📊

A lightweight market monitoring dashboard built with **Python and Streamlit**, designed to quickly compare the performance of major stock market indices, sector ETFs, and other financial instruments.

The application provides a clear overview of short-term market movements, helping identify relative strength, weakness, and potential market rotation.

## Features

- **Market overview** – monitor indices, sectors, ETFs, and selected financial instruments.
- **Performance comparison** – percentage price changes over 1, 3, and 5 trading days.
- **Interactive sorting** – sort instruments by individual columns to identify market leaders and laggards.
- **Color-coded performance** – green for positive returns and red for negative returns.
- **Instrument tooltips** – hover over ticker symbols to display their descriptions.
- **Latest available prices** – retrieve historical market data using Yahoo Finance.
- **Data status indicators** – identify successfully retrieved data.
- **Streamlit interface** – a lightweight dashboard with a custom HTML-based table.

## Technologies

- Python
- Streamlit
- yfinance
- pandas
- HTML / CSS

## How It Works

The application retrieves market data from Yahoo Finance and calculates percentage price changes across multiple trading periods.

The percentage change is calculated as:

**Percentage Change = ((Current Price / Previous Price) - 1) × 100**

The results are displayed in an interactive table, allowing users to compare market performance and quickly identify areas of interest.

## Purpose

The primary goal is to provide a fast, easy-to-read market overview without unnecessary technical indicators or complex charts.

The dashboard is designed as an initial screening tool rather than a complete trading system.

A typical workflow:

1. Review market performance.
2. Sort instruments by percentage change.
3. Identify relative strength, weakness, or potential recovery.
4. Perform further technical analysis using external charting tools.

## Data Source

Market data is provided by **Yahoo Finance** through the `yfinance` Python library.

Data availability and accuracy depend on the external provider. Some instruments may have delayed or missing data.

## Disclaimer

This project is intended for educational purposes and personal market analysis only.

It does not provide investment advice or automated trading recommendations.

## Project Status

**Functional – under ongoing development.**

The core market monitoring functionality is implemented. Future improvements will be based on practical usage and identified needs.

## Author

Developed as a personal Python and financial data analysis project.
