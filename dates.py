"""Date values used by goods and warehouse documents."""

import re
from datetime import date, datetime


def parse_issue_date(value):
    """Accept a real calendar date in the visible YYYY-MM-DD format."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError("Podaj datę wystawienia w formacie RRRR-MM-DD.")
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValueError("Podaj istniejącą datę wystawienia w formacie RRRR-MM-DD.") from error


def issue_date_text(value):
    return "Brak daty" if value is None else parse_issue_date(value).isoformat()


def timestamp_text(value):
    if value is None:
        return "Brak daty"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)[:16]


def today_text():
    return date.today().isoformat()
