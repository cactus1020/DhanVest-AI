"""Import verified, genuinely dated history without clearing existing data."""
import argparse
import math

from backend.data_validation import load_market_data, validate_source
from frontend.api.index import database_request


def optional(row, field):
    value = row.get(field)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return value


def seed_database(path, source_url, confirm_verified=False):
    # Validate the entire file before making a single database write.
    frame = load_market_data(path)
    validate_source(source_url)
    if not confirm_verified:
        raise ValueError("Verify this file against its source, then pass --confirm-verified. Never mark the old undated CSV as verified.")
    symbols = frame["symbol"].unique()
    stock_map = {}
    for symbol in symbols:
        existing = database_request("GET", "stocks", params={"select": "id", "symbol": "eq." + symbol})
        if existing:
            stock_map[symbol] = existing[0]["id"]
            continue
        first = frame[frame["symbol"] == symbol].iloc[0]
        created = database_request("POST", "stocks", body={"symbol": symbol, "name": optional(first, "name") or symbol, "sector": optional(first, "sector")}, prefer="return=representation")
        stock_map[symbol] = created[0]["id"]
    rows = []
    for _, row in frame.iterrows():
        fundamentals_date = row.get("fundamentals_date")
        import pandas as pd
        fundamentals_date = None if pd.isna(fundamentals_date) else fundamentals_date.date().isoformat()
        rows.append({
            "stock_id": stock_map[row["symbol"]], "date": row["date"].date().isoformat(),
            "close_price": float(row["close"]), "volume": int(row["volume"]),
            "pe_ratio": optional(row, "pe_ratio"), "roe": optional(row, "roe"),
            "debt_to_equity": optional(row, "debt_to_equity"),
            "fundamentals_date": fundamentals_date, "source_url": source_url, "source_verified": True,
        })
    for start in range(0, len(rows), 500):
        database_request("POST", "daily_data", params={"on_conflict": "stock_id,date"}, body=rows[start:start + 500], prefer="resolution=merge-duplicates,return=minimal")
    print(f"Imported {len(rows)} verified rows for {len(symbols)} stocks. Existing history was preserved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--confirm-verified", action="store_true")
    args = parser.parse_args()
    try:
        seed_database(args.csv, args.source_url, args.confirm_verified)
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
