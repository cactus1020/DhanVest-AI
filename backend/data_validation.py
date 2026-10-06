"""Validate sourced CSV data before any database writes or model training."""
from datetime import date
from urllib.parse import urlparse

import pandas as pd


def load_market_data(path, special_sessions=()):
    frame = pd.read_csv(path)
    required = {"symbol", "date", "close", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)) + ". Real trading dates are required; dates will never be invented.")
    if frame.empty:
        raise ValueError("Market data is empty.")
    frame["symbol"] = frame["symbol"].astype("string").str.strip()
    if frame["symbol"].isna().any() or frame["symbol"].eq("").any():
        raise ValueError("Every row requires a stock symbol.")
    raw_dates = frame["date"].astype("string")
    if not raw_dates.str.fullmatch(r"\d{4}-\d{2}-\d{2}").fillna(False).all():
        raise ValueError("Trading dates must use YYYY-MM-DD.")
    frame["date"] = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")
    if frame["date"].isna().any() or (frame["date"].dt.date > date.today()).any():
        raise ValueError("Trading dates contain invalid or future dates.")
    if (frame["date"].dt.dayofweek.isin([4, 5]) & ~frame["date"].dt.strftime("%Y-%m-%d").isin(special_sessions)).any():
        raise ValueError("DSE trading dates cannot be Friday or Saturday. Verify the source calendar.")
    for column in ["close", "volume", "pe_ratio", "roe", "debt_to_equity"]:
        if column in frame:
            original = frame[column]
            frame[column] = pd.to_numeric(original, errors="coerce")
            if (original.notna() & frame[column].isna()).any() or frame[column].isin([float('inf'), float('-inf')]).any():
                raise ValueError(f"Invalid numeric values in {column}.")
    if frame[["close", "volume"]].isna().any().any() or (frame["close"] <= 0).any() or (frame["volume"] < 0).any():
        raise ValueError("Prices must be positive and volume must be non-negative.")
    if (frame["volume"] % 1 != 0).any():
        raise ValueError("Volume must be a whole number.")
    for column in ["pe_ratio", "debt_to_equity"]:
        if column in frame and (frame[column].dropna() < 0).any():
            raise ValueError(f"{column} cannot be negative.")
    if "fundamentals_date" in frame:
        parsed = pd.to_datetime(frame["fundamentals_date"], format="%Y-%m-%d", errors="coerce")
        if (frame["fundamentals_date"].notna() & parsed.isna()).any() or (parsed > frame["date"]).any():
            raise ValueError("Fundamental reporting dates must be valid and cannot follow their market snapshot.")
        frame["fundamentals_date"] = parsed
    if frame.duplicated(["symbol", "date"]).any():
        raise ValueError("Duplicate symbol/date rows must be resolved at the source.")
    return frame.sort_values(["symbol", "date"]).reset_index(drop=True)


def validate_source(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Provide an HTTPS source URL without credentials.")
    return url
