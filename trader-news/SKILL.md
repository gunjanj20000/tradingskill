---
name: trader-news
description: "News and corporate sentiment monitor for Indian stocks (NSE/BSE). Scrapes breaking news, quarterly earnings releases, board meetings, and regulatory developments with automated sentiment analysis."
---

# News & Sentiment Monitor (`trader-news`)

Monitors market news, earnings updates, and corporate actions across Indian stocks.

## Features
- **Indian Financial Coverage**: Aggregates headlines for `.NS` stocks.
- **Categorization**: Tags stories into `EARNINGS`, `CORP_ACTION`, `REGULATORY`, `CONTRACT_WIN`, and `BROKER_RATING`.
- **Sentiment Classification**: Detects `BULLISH`, `BEARISH`, or `NEUTRAL` market impact.

## CLI Usage

```bash
# Get news and sentiment for a single stock
python3 trader-news/news.py --symbol SBIN.NS

# Batch check news for multiple tickers
python3 trader-news/news.py --symbols RELIANCE.NS,TCS.NS,HDFCBANK.NS

# Output JSON
python3 trader-news/news.py --symbol INFY.NS --json
```
