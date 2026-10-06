"""Collect official dated headlines for a research price/news dataset."""
import hashlib,json,time,re
from frontend.api.index import read_all
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlencode
from frontend.market_data import fetch_json,BASE

def main():
    folder=Path('data/dse-news-20261006');folder.mkdir(exist_ok=True)
    companies=sorted(row['symbol'] for row in read_all('stocks'))
    events={};failed=[]
    for symbol in companies:
        target=folder/(symbol+'.json')
        if target.exists():items=json.loads(target.read_text(encoding='utf-8'))
        else:
            try:
                data=fetch_json('/api/live/news',{'code':symbol,'from':'2024-10-06','to':'2026-10-06'},ttl=1)
                if data.get('truncated'):raise ValueError('News response truncated; split range before using it')
                items=[]
                for row in data.get('rows',[]):
                    if row.get('code')!=symbol:continue
                    day=date.fromisoformat(row['filedAt'][:10])
                    if not date(2024,10,6)<=day<=date(2026,10,6):continue
                    title=row.get('summary')
                    if not title or not row.get('id'):continue
                    available=(datetime.combine(day+timedelta(days=1),datetime.min.time()).replace(tzinfo=__import__('zoneinfo').ZoneInfo('Asia/Dhaka'))).isoformat()
                    items.append({'event_id':hashlib.sha256(('DSE:'+str(row['id'])).encode()).hexdigest(),'symbols':[symbol],'title':title,'kind':'official','event_type':row.get('type'), 'positive_keyword_count':len(re.findall(r'\b(?:increase|growth|profit|dividend|approved|expansion)\b',str(row.get('body','')),re.I)), 'negative_keyword_count':len(re.findall(r'\b(?:decrease|loss|decline|penalty|suspended|default)\b',str(row.get('body','')),re.I)), 'published_date':day.isoformat(),'available_at':available,'availability_basis':'archive_reconstruction','retrieved_at':datetime.now(timezone.utc).isoformat(),'source_url':BASE+'/api/live/news?'+urlencode({'code':symbol})})
                with target.open('x',encoding='utf-8') as f:json.dump(items,f,ensure_ascii=False)
            except Exception as error:failed.append({'symbol':symbol,'error':type(error).__name__});print(symbol,'FAILED',type(error).__name__,flush=True);continue
        for event in items:
            prior=events.get(event['event_id'])
            if prior:prior['symbols']=sorted(set(prior['symbols']+event['symbols']))
            else:events[event['event_id']]=event
        print(symbol,len(items),'official headline events',flush=True);time.sleep(.2)
    with (folder/'events.jsonl').open('w',encoding='utf-8') as f:
        for event in events.values():f.write(json.dumps(event,ensure_ascii=False)+'\n')
    (folder/'manifest.json').write_text(json.dumps({'events':len(events),'companies':len(companies),'failures':failed,'limitations':['DSE announcements only; newspapers are not yet included.','Date-only availability reconstructed conservatively to next day; revisions not verified.','Not a proven real-time backtest archive.']},indent=2),encoding='utf-8')
    print('Saved',len(events),'events; failures:',len(failed),flush=True)

if __name__=='__main__':main()
