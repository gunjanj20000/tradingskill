"""Indian Equities Universes: Nifty 50, Nifty Bank, Nifty Next 50, and Liquid F&O.

Default symbol convention uses National Stock Exchange of India (NSE) '.NS' suffix
compatible with Yahoo Finance and standard quantitative platforms.
"""

# Nifty 50 constituents (50 bluechip liquid Indian stocks)
NIFTY_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "BHARTIARTL.NS", "ICICIBANK.NS",
    "INFY.NS", "SBIN.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS",
    "KOTAKBANK.NS", "NTPC.NS", "ONGC.NS", "TITAN.NS", "AXISBANK.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "POWERGRID.NS", "COALINDIA.NS", "TATASTEEL.NS",
    "BAJAJFINSV.NS", "M&M.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "JSWSTEEL.NS",
    "GRASIM.NS", "TECHM.NS", "HINDALCO.NS", "WIPRO.NS", "CIPLA.NS",
    "NESTLEIND.NS", "DRREDDY.NS", "TATACONSUM.NS", "BPCL.NS", "APOLLOHOSP.NS",
    "EICHERMOT.NS", "SBILIFE.NS", "BRITANNIA.NS", "HEROMOTOCO.NS", "DIVISLAB.NS",
    "BAJAJ-AUTO.NS", "SHRIRAMFIN.NS", "BEL.NS", "TRENT.NS", "INDUSINDBK.NS",
]

# Nifty Bank constituents (12 liquid banking stocks)
NIFTY_BANK = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "AUBANK.NS", "FEDERALBNK.NS",
    "IDFCFIRSTB.NS", "BANDHANBNK.NS",
]

# Nifty Next 50 constituents (large-to-mid growth leaders)
NIFTY_NEXT_50 = [
    "ZOMATO.NS", "JIOFIN.NS", "HAL.NS", "VEDL.NS", "DLF.NS",
    "BHEL.NS", "CHOLAFIN.NS", "DIXON.NS", "POLYCAB.NS", "SIEMENS.NS",
    "ABB.NS", "CANBK.NS", "HAVELLS.NS", "AMBUJACEM.NS", "GAIL.NS",
    "PFC.NS", "RECLTD.NS", "IOC.NS", "TVSMOTOR.NS", "MOTHERSON.NS",
    "INDIGO.NS", "CGPOWER.NS", "CUMMINSIND.NS", "BOSCHLTD.NS", "COLPAL.NS",
    "LTIM.NS", "PIDILITIND.NS", "SRF.NS", "VOLTAS.NS", "PERSISTENT.NS",
    "IRFC.NS", "RVNL.NS", "MAXHEALTH.NS", "GODREJCP.NS", "DABUR.NS",
    "MUTHOOTFIN.NS", "OBEROIRLTY.NS", "JSWENERGY.NS", "TORNTPOWER.NS", "UNITDSPR.NS",
    "NAUKRI.NS", "ICICIPRULI.NS", "ICICIGI.NS", "HDFCLIFE.NS", "TATACHEM.NS",
    "BERGEPAINT.NS", "MARICO.NS", "LODHA.NS", "PHOENIXLTD.NS", "TATAPOWER.NS",
]

# High-liquidity F&O universe (Top ~60 day trading intraday favorites)
FNO_TOP = list(dict.fromkeys(NIFTY_50 + NIFTY_BANK + [
    "HAL.NS", "BEL.NS", "ZOMATO.NS", "DLF.NS", "VEDL.NS", "BHEL.NS",
    "CHOLAFIN.NS", "DIXON.NS", "POLYCAB.NS", "TRENT.NS", "TATAPOWER.NS",
    "RECLTD.NS", "PFC.NS", "TVSMOTOR.NS", "INDIGO.NS", "PERSISTENT.NS"
]))

UNIVERSES = {
    "nifty50": NIFTY_50,
    "niftybank": NIFTY_BANK,
    "niftynext50": NIFTY_NEXT_50,
    "fno": FNO_TOP,
}


def clean_symbol(symbol: str) -> str:
    """Normalize Indian stock symbol to standard Yahoo Finance '.NS' format.
    
    Examples:
        'RELIANCE' -> 'RELIANCE.NS'
        'reliance' -> 'RELIANCE.NS'
        'RELIANCE.NS' -> 'RELIANCE.NS'
        '500325.BO' -> '500325.BO'
    """
    s = symbol.strip().upper()
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    return f"{s}.NS"


def get_universe(name: str) -> list[str]:
    """Retrieve list of tickers for a named universe."""
    key = name.lower().replace("-", "").replace("_", "").replace(" ", "")
    for u_key, symbols in UNIVERSES.items():
        if key in u_key or u_key in key:
            return list(symbols)
    raise ValueError(f"Unknown universe '{name}'. Available: {list(UNIVERSES.keys())}")
