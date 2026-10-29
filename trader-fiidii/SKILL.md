---
name: trader-fiidii
description: "Institutional activity tracker for Indian stocks (NSE/BSE). Monitors daily Foreign Institutional (FII) & Domestic Institutional (DII) cash flows, NSE Bulk & Block deals, and SEBI promoter insider trading filings."
---

# Institutional Tracker (`trader-fiidii`)

Monitors institutional money flow (the "Smart Money") driving Indian equity markets.

## Features
- **Daily FII / DII Cash Flows**: Net buy/sell figures in ₹ Crores.
- **FII Derivatives Sentiment**: FII Index Futures Long/Short ratio.
- **NSE Bulk & Block Deals**: Institutional trades exceeding 0.5% of company equity.
- **SEBI PIT Insider Disclosures**: Tracks open-market purchases by promoters, directors, and key management.

## CLI Usage

```bash
# View daily FII / DII net cash & derivative positions
python3 trader-fiidii/fiidii.py flows

# View recent NSE bulk and block deals
python3 trader-fiidii/fiidii.py bulk

# View promoter insider trading disclosures
python3 trader-fiidii/fiidii.py insider

# Check institutional flows & block deals for a specific stock
python3 trader-fiidii/fiidii.py check SBIN.NS
```
