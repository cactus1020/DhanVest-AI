"""Import owned DSE source exports into separate verified history; never replace legacy rows."""
import json
from pathlib import Path
from urllib.parse import urlencode
from backend.data_validation import load_market_data
from frontend.api.index import read_all,database_request

path=Path('data/dse-history-20261006/dated-prices.csv')
frame=load_market_data(path,special_sessions=('2025-05-17','2025-05-24','2026-05-23'))
mapping={row['symbol']:row['id'] for row in read_all('stocks')}
missing=set(frame['symbol'])-set(mapping)
if missing:raise ValueError('Missing stocks: '+','.join(sorted(missing)))
records=[]
for symbol,group in frame.groupby('symbol'):
    source='https://www.dsebd.org/api/live/data-archive/day-end?'+urlencode({'inst':symbol,'from':group['date'].min().date().isoformat(),'to':group['date'].max().date().isoformat()})
    for _,row in group.iterrows():
        records.append({'stock_id':mapping[symbol],'date':row['date'].date().isoformat(),'close_price':float(row['close']),'volume':int(row['volume']),'source_url':source,'source_verified':True})
for offset in range(0,len(records),500):
    database_request('POST','market_history',params={'on_conflict':'stock_id,date'},body=records[offset:offset+500],prefer='resolution=ignore-duplicates,return=minimal')
    print('Processed',min(offset+500,len(records)),'/',len(records),flush=True)
print('Verified backfill completed. Legacy daily_data and saved scores were untouched.',flush=True)
