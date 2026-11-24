"""
Parses a historical-price CSV into (date, close_price) pairs. Deliberately
tolerant of common header variants (date/Date, close/Close/close_price)
since price exports from different sources (NSE bhavcopy, broker exports,
manually assembled sheets) don't agree on a convention — but strict about
the data itself: any row that doesn't parse cleanly is reported back by
row number rather than silently skipped or guessed at.
"""

import csv
import datetime
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

DATE_COLUMN_ALIASES = {"date", "price_date", "trade_date"}
CLOSE_COLUMN_ALIASES = {"close", "close_price", "closing_price", "ltp", "price"}

DATE_FORMATS = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"]


@dataclass
class ParsedPriceRow:
    price_date: datetime.date
    close_price: Decimal


@dataclass
class ParseResult:
    rows: list[ParsedPriceRow]
    errors: list[str]  # human-readable, e.g. "Row 4: could not parse date 'N/A'"


def _find_column(fieldnames: list[str], aliases: set[str]) -> str | None:
    lowered = {f.lower().strip(): f for f in fieldnames}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    return None


def _parse_date(raw: str) -> datetime.date | None:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_price_csv(content: bytes) -> ParseResult:
    text = content.decode("utf-8-sig")  # handles Excel's BOM-prefixed exports
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return ParseResult(rows=[], errors=["File appears to be empty or not a valid CSV."])

    date_col = _find_column(reader.fieldnames, DATE_COLUMN_ALIASES)
    close_col = _find_column(reader.fieldnames, CLOSE_COLUMN_ALIASES)

    if date_col is None or close_col is None:
        return ParseResult(
            rows=[],
            errors=[
                f"Could not find date/close columns. Found headers: {reader.fieldnames}. "
                f"Expected a date column ({', '.join(sorted(DATE_COLUMN_ALIASES))}) and a "
                f"close-price column ({', '.join(sorted(CLOSE_COLUMN_ALIASES))})."
            ],
        )

    rows: list[ParsedPriceRow] = []
    errors: list[str] = []

    for i, record in enumerate(reader, start=2):  # row 1 is the header
        raw_date = (record.get(date_col) or "").strip()
        raw_close = (record.get(close_col) or "").strip()

        if not raw_date and not raw_close:
            continue  # skip blank lines

        parsed_date = _parse_date(raw_date)
        if parsed_date is None:
            errors.append(f"Row {i}: could not parse date '{raw_date}'")
            continue

        try:
            close_price = Decimal(raw_close.replace(",", ""))
        except InvalidOperation:
            errors.append(f"Row {i}: could not parse close price '{raw_close}'")
            continue

        if close_price <= 0:
            errors.append(f"Row {i}: close price must be positive, got '{raw_close}'")
            continue

        rows.append(ParsedPriceRow(price_date=parsed_date, close_price=close_price))

    return ParseResult(rows=rows, errors=errors)
