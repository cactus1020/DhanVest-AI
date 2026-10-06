"""Download date-validated DSE history without changing any database."""
import csv
import hashlib
import json
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from time import sleep
from frontend.market_data import company_history, market_snapshot
from frontend.api.index import read_all

def main():
    root=Path('data/dse-history-20261006');root.mkdir(parents=True,exist_ok=True)
    snapshot=market_snapshot()
    existing={row['symbol'] for row in read_all('stocks')}
    candidates=sorted(snapshot['quotes'],key=lambda row:(row['symbol'] not in existing,-row['volume']))
    selected=[quote for quote in candidates if quote['traded']][:50]
    end=date.fromisoformat(snapshot['session']['sessionDate'])
    start=end.replace(year=end.year-5)
    sources=[];counts={};all_rows=[];failures=[]
    for quote in selected:
        symbol=quote['symbol'];target=root/(symbol+'.json')
        if target.exists():
            records=json.loads(target.read_text(encoding='utf-8'))
        else:
            records=[];cursor=start
            try:
                while cursor<=end:
                    stop=min(cursor+timedelta(days=364),end)
                    data=company_history(symbol,cursor.isoformat(),stop.isoformat())
                    sources.append({'symbol':symbol,'from':cursor.isoformat(),'to':stop.isoformat(),'url':data['source_url'],'count':len(data['points']),'excluded_out_of_range':data['excluded_out_of_range']})
                    records.extend(data['points']);cursor=stop+timedelta(days=1)
                    sleep(.2)
                if len({row['date'] for row in records})!=len(records):raise ValueError('Duplicate dates')
                with target.open('x',encoding='utf-8') as f:json.dump(records,f)
            except Exception as error:
                failures.append({'symbol':symbol,'error':type(error).__name__});print(symbol,'FAILED',type(error).__name__,flush=True);continue
        for row in records:all_rows.append(dict(row,symbol=symbol,sector=quote['sector']))
        counts[symbol]=len(records);print(symbol,len(records),'dated records',flush=True)
    output=root/'dated-prices.csv'
    # CSV is derived from immutable per-symbol source exports; original files are preserved.
    with output.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['symbol','date','close','volume','open','high','low','sector']);writer.writeheader();writer.writerows(all_rows)
    manifest={'retrieved_at':datetime.now(timezone.utc).isoformat(),'requested_start':start.isoformat(),'requested_end':end.isoformat(),'source':'DSE public archive','symbols':counts,'rows':len(all_rows),'actual_first_date':min((row['date'] for row in all_rows),default=None),'actual_last_date':max((row['date'] for row in all_rows),default=None),'failed_symbols':failures,'queries':sources,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'limitations':['Current liquid-stock universe introduces survivorship/selection bias.','Corporate-action adjustments have not been established.','Public website access does not establish commercial redistribution rights.','News and fundamentals are not included.']}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Saved',len(all_rows),'observations for',len(counts),'companies; failures:',len(failures),flush=True)

if __name__=='__main__':main()
