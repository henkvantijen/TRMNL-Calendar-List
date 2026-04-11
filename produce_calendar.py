#!/usr/bin/env python3
# fethches google calender items to display those on TRMN device
# this script puts cal items in json file, somewhere on your public server, 
# the TRML plugin fetches the json file periodically
# produce_calendar.py — run every 15 minutes via cron:
# */15 * * * * /usr/bin/python3 /home/youruser/produce_calendar.py
# Once:
# pip install requests icalendar --break-system-packages

import json
import requests
from datetime  import date, datetime, timezone
from icalendar import Calendar

# --- Configuration ---
#ICAL_URL     = "https://calendar.google.com/calendar/ical/YOUR_SECRET_URL/basic.ics"
ICAL_URL     = "https://calendar.google.com/calendar/ical/<name>/private-<id_code>/basic.ics"
OUTPUT_PATH  = "/var/www/html/<domain>/cal/calendar.json"
MAX_EVENTS   = 10
YOUR_TIMEZONE = "Europe/Amsterdam"   # adjust to your local timezone
# ---------------------

import zoneinfo
TZ = zoneinfo.ZoneInfo(YOUR_TIMEZONE)

def get_dt(component):
    """Return a timezone-aware datetime for a VEVENT's DTSTART.
    All-day events (date only) are given midnight local time."""
    dt = component.decoded("DTSTART")
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    else:
        # all-day event: date object → treat as midnight local
        return datetime(dt.year, dt.month, dt.day, 0, 0, tzinfo=TZ)

def main():
    response = requests.get(ICAL_URL, timeout=10)
    response.raise_for_status()
    cal = Calendar.from_ical(response.content)

   today_start = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)

    events = []
    for component in cal.walk("VEVENT"):
        try:
            dt = get_dt(component)
        except Exception:
            continue
        if dt < today_start:
            continue
        summary = str(component.get("SUMMARY", "(no title)"))
        events.append({
            "dt":      dt,
            "weekday": dt.strftime("%A"),          # e.g. "Wednesday"
            "day":     dt.strftime("%d"),          # zero-padded: 01, 09, 31
            "time":    dt.strftime("%H:%M"),       # e.g. "09:15"
            "title":   summary,
        })

    # Sort by start time, take max 10
    events.sort(key=lambda e: e["dt"])
    events = events[:MAX_EVENTS]

    # Suppress repeated weekday labels
    last_weekday = None
    rows = []
    for e in events:
        rows.append({
            "weekday": e["weekday"] if e["weekday"] != last_weekday else "",
            "day":     e["day"]     if e["weekday"] != last_weekday else "",
            "time":    e["time"],
            "title":   e["title"],
        })
        last_weekday = e["weekday"]

    output = {
        "updated_at": datetime.now(TZ).strftime("%d %b %H:%M"),
        "event_count": str(len(rows)),
        "events": rows
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
