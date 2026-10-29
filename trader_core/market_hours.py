"""Indian Market Hours & Calendar Utilities (NSE/BSE).

Timezone: Asia/Kolkata (IST: UTC+05:30)
Regular Trading: 09:15 AM - 03:30 PM IST (Mon - Fri)
Pre-market: 09:00 AM - 09:08 AM IST
Intraday Entry Window: 09:20 AM - 02:45 PM IST
Mandatory MIS Flat-by Cutoff: 03:15 PM IST
"""

import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# NSE/BSE Trading Holidays for 2026
NSE_HOLIDAYS_2026 = {
    "2026-01-26": "Republic Day",
    "2026-02-17": "Mahashivratri",
    "2026-03-03": "Holi",
    "2026-03-20": "Id-Ul-Fitr (Ramzan Id)",
    "2026-03-31": "Mahavir Jayanti",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day / Labour Day",
    "2026-05-27": "Bakri Id (Id-Ul-Zuha)",
    "2026-06-26": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-09-04": "Janmashtami",
    "2026-09-14": "Milad-Un-Nabi",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-08": "Diwali Laxmi Pujan (Muhurat trading session only)",
    "2026-11-10": "Diwali Balipratipada",
    "2026-11-24": "Gurunanak Jayanti",
    "2026-12-25": "Christmas",
}


def now_ist() -> datetime.datetime:
    """Get current datetime in IST."""
    return datetime.datetime.now(IST)


def parse_ist(dt_str: str) -> datetime.datetime:
    """Parse a datetime string in IST.
    Supports formats:
      'YYYY-MM-DD HH:MM:SS'
      'YYYY-MM-DD HH:MM'
      'YYYY-MM-DD'
    """
    dt_str = dt_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(dt_str, fmt)
            return dt.replace(tzinfo=IST)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date/time format: {dt_str}")


def is_trading_day(dt: datetime.datetime) -> bool:
    """Check if date is an active NSE trading day (weekday and not a holiday)."""
    dt_local = dt.astimezone(IST)
    if dt_local.weekday() >= 5:  # Saturday or Sunday
        return False
    date_str = dt_local.strftime("%Y-%m-%d")
    return date_str not in NSE_HOLIDAYS_2026


def is_market_open(dt: datetime.datetime | None = None) -> bool:
    """Check if normal market trading is actively ongoing (09:15 - 15:30 IST)."""
    curr = dt.astimezone(IST) if dt else now_ist()
    if not is_trading_day(curr):
        return False
    open_time = datetime.time(9, 15)
    close_time = datetime.time(15, 30)
    return open_time <= curr.time() <= close_time


def is_entry_allowed(
    dt: datetime.datetime | None = None,
    no_entries_before: str = "09:20",
    no_entries_after: str = "14:45",
) -> tuple[bool, str]:
    """Check if new intraday day-trade entries are permitted.
    
    Default rules:
    - No entries before 09:20 AM IST (let initial opening volatility stabilize).
    - No entries after 02:45 PM IST (insufficient time for trade development before 03:15 PM square off).
    """
    curr = dt.astimezone(IST) if dt else now_ist()
    if not is_trading_day(curr):
        date_str = curr.strftime("%Y-%m-%d")
        holiday = NSE_HOLIDAYS_2026.get(date_str)
        if holiday:
            return False, f"Market is closed today ({holiday})"
        return False, "Market is closed (Weekend)"

    t_before = datetime.datetime.strptime(no_entries_before, "%H:%M").time()
    t_after = datetime.datetime.strptime(no_entries_after, "%H:%M").time()
    curr_time = curr.time()

    if curr_time < t_before:
        return False, f"Too early: entries open at {no_entries_before} IST (current {curr_time.strftime('%H:%M')})"
    if curr_time > t_after:
        return False, f"Too late: intraday entries cut off at {no_entries_after} IST (current {curr_time.strftime('%H:%M')})"

    return True, "Entry window is open"
