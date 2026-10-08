"""Bounded refresh of reported annual facts; reviewed ratios are preserved."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from time import monotonic
import hashlib,json
try:
    from .fundamentals import fetch_company,normalize_company
except ImportError:
    from fundamentals import fetch_company,normalize_company

def capture(stocks, fetch=fetch_company, prioritized=()):
    mapping={row['symbol']:row['id'] for row in stocks}
    symbols=list(mapping)+(['BSCPLC'] if 'BSCPLC' not in mapping else [])
    symbols.sort(key=lambda symbol:symbol not in prioritized)
    records=[];failed=[];count=0;started=monotonic()
    def collect(symbol):
        profile=fetch(symbol);items=normalize_company(profile,mapping.get(symbol))
        if symbol not in mapping and items:
            item=max(items,key=lambda r:r['period_end'])
            item.update(benchmark_price=profile['price'],price_date=profile['asOfDate'])
            signature={k:v for k,v in item.items() if k not in ('record_id','source_observed_at')}
            item['record_id']=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest();items=[item]
        return items
    with ThreadPoolExecutor(max_workers=4) as pool:
        for offset in range(0,len(symbols),4):
            if monotonic()-started>20:failed.extend(symbols[offset:]);break
            pending={pool.submit(collect,symbol):symbol for symbol in symbols[offset:offset+4]}
            for future in as_completed(pending):
                try:records.extend(future.result());count+=1
                except Exception:failed.append(pending[future])
    return records,count,failed

def install(app,database_request,read_all,authorized):
    from fastapi import Request
    @app.get('/api/jobs/fundamentals-sync')
    def sync(request:Request):
        authorized(request)
        previous=database_request('GET','dhanvest_fundamental_runs',params={'select':'failed_symbols','order':'id.desc','limit':1})
        run=database_request('POST','dhanvest_fundamental_runs',body={'status':'running'},prefer='return=representation')[0]
        try:
            stocks=read_all('stocks')
            retry=(previous[0].get('failed_symbols') or []) if previous else []
            stocks.sort(key=lambda row:row['symbol'] not in retry)
            records,count,failed=capture(stocks,prioritized=retry)
            if records:
                database_request('POST','dhanvest_fundamentals',params={'on_conflict':'record_id'},body=records,
                                 prefer='resolution=ignore-duplicates,return=minimal')
            status='partial' if failed else 'complete'
            database_request('PATCH','dhanvest_fundamental_runs',params={'id':'eq.'+str(run['id'])},body={
              'status':status,'finished_at':datetime.now(timezone.utc).isoformat(),'company_count':count,
              'observed_records':len(records),'failed_symbols':failed})
            return {'status':status,'company_count':count,'observed_records':len(records),'failed_symbols':failed}
        except Exception:
            database_request('PATCH','dhanvest_fundamental_runs',params={'id':'eq.'+str(run['id'])},body={
              'status':'failed','finished_at':datetime.now(timezone.utc).isoformat()})
            raise
