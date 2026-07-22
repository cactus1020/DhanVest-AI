import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

def seed_database():
    # We will fetch credentials from the ar-shop env file
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'Ai for antigravity', 'ar-shop', '.env')
    load_dotenv(env_path)
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from ar-shop/.env")
        return
        
    supabase: Client = create_client(url, key)
    
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'real_dse_data.csv')
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # 1. Extract unique stocks
    print("Extracting unique stocks...")
    unique_symbols = df['symbol'].unique()
    
    stocks_to_insert = []
    for symbol in unique_symbols:
        stocks_to_insert.append({
            "symbol": str(symbol),
            "name": f"{symbol} Limited", # We don't have real names in CSV, using placeholder
            "sector": "General" # We don't have sector info in CSV, using placeholder
        })
    
    print(f"Upserting {len(stocks_to_insert)} stocks to Supabase...")
    # Insert stocks (using upsert to avoid duplicate key errors)
    for i in range(0, len(stocks_to_insert), 100):
        batch = stocks_to_insert[i:i+100]
        try:
            supabase.table('stocks').upsert(batch, on_conflict='symbol').execute()
        except Exception as e:
            print(f"Error upserting stocks batch: {e}")
            
    # Fetch all stocks to get their IDs
    response = supabase.table('stocks').select('id, symbol').execute()
    stock_map = {item['symbol']: item['id'] for item in response.data}
    
    # 2. Prepare daily data
    print("Preparing daily data for insertion...")
    daily_data_to_insert = []
    
    # Sort by date if we had a date column. The CSV has rows but no date! 
    # Let's generate dates backwards from today since it's historical data, assuming 1 row per day.
    # Wait, the real DSE CSV probably has dates? Let's check the dataframe.
    if 'date' in df.columns:
        df['date_val'] = pd.to_datetime(df['date'])
    else:
        # If no date column, we'll assign a mock date based on index per symbol (from oldest to newest)
        print("No date column found! Generating sequential dates...")
        
    import datetime
    today = datetime.datetime.now().date()
    
    for symbol in unique_symbols:
        stock_id = stock_map.get(str(symbol))
        if not stock_id:
            continue
            
        stock_df = df[df['symbol'] == symbol].copy()
        
        # Keep only the last 365 rows for sanity
        stock_df = stock_df.tail(365)
        
        num_rows = len(stock_df)
        
        for idx in range(num_rows):
            row = stock_df.iloc[idx]
            
            # Use 'ltp' or 'close' as price, 'volume' as volume
            close_price = float(row.get('close', row.get('ltp', 0)))
            volume = int(row.get('volume', 0))
            
            # Generate date (last row is today, going backwards)
            days_ago = num_rows - 1 - idx
            row_date = today - datetime.timedelta(days=days_ago)
            
            daily_data_to_insert.append({
                "stock_id": stock_id,
                "date": row_date.isoformat(),
                "close_price": close_price,
                "volume": volume,
                # Set fundamentals to None
                "pe_ratio": None,
                "roe": None,
                "debt_to_equity": None
            })
            
    print(f"Uploading {len(daily_data_to_insert)} daily data records to Supabase...")
    # Batch insert daily data
    # First, let's clear the existing data just in case
    supabase.table('daily_data').delete().neq('id', 0).execute()
    
    batch_size = 500
    for i in range(0, len(daily_data_to_insert), batch_size):
        batch = daily_data_to_insert[i:i+batch_size]
        try:
            supabase.table('daily_data').insert(batch).execute()
            if (i % 5000 == 0) and i > 0:
                print(f"Uploaded {i} records...")
        except Exception as e:
            print(f"Error inserting daily data batch {i}: {e}")
            
    print("Database seed completed successfully!")

if __name__ == "__main__":
    seed_database()
