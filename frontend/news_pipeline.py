"""Capture announcement versions as actually observed; never backdate availability."""
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode
from time import monotonic
from zoneinfo import ZoneInfo

try:
    from .market_data import fetch_json, BASE
except ImportError:
    from market_data import fetch_json, BASE


def normalize_rows(data, symbol, observed_at):
    if not isinstance(data.get('rows'), list) or data.get('truncated'):
        raise ValueError('Incomplete announcement response')
    observed = datetime.fromisoformat(observed_at)
    events = {}
    for row in data['rows']:
        if row.get('code') != symbol:
            continue
        title = str(row.get('summary') or '').strip()
        source_id = str(row.get('id') or '')
        published = date.fromisoformat(str(row.get('filedAt'))[:10])
        if not source_id or not 1 <= len(title) <= 1000 or published > observed.astimezone(ZoneInfo('Asia/Dhaka')).date():
            raise ValueError('Invalid announcement metadata')
        body = str(row.get('body') or '')
        content_hash = hashlib.sha256((title+'\n'+body).encode()).hexdigest()
        event_id = hashlib.sha256(('DSE:'+source_id+':'+content_hash).encode()).hexdigest()
        events[event_id] = {'event_id':event_id,'source_event_id':source_id,'title':title,
            'symbols':[symbol],'kind':'official','published_date':published.isoformat(),
            'first_seen_at':observed_at,'available_at':observed_at,'availability_basis':'prospective_capture',
            'source_url':BASE+'/api/live/news?'+urlencode({'code':symbol}), 'content_hash':content_hash,
            'positive_keyword_count':len(re.findall(r'\b(?:increase|growth|profit|dividend|approved|expansion)\b',body,re.I)),
            'negative_keyword_count':len(re.findall(r'\b(?:decrease|loss|decline|penalty|suspended|default)\b',body,re.I))}
    return list(events.values())


def capture_symbols(symbols, fetch=fetch_json):
    # Small batches and a deadline keep this within the serverless runtime.
    started = monotonic(); events = {}; failed = []; done = 0
    symbols = list(dict.fromkeys(symbols))[:50]
    end = datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Dhaka')).date(); start = end-timedelta(days=14)
    def collect(symbol):
        data = fetch('/api/live/news',{'code':symbol,'from':start.isoformat(),'to':end.isoformat()},ttl=1)
        observed = datetime.now(timezone.utc).isoformat()
        return normalize_rows(data,symbol,observed)
    with ThreadPoolExecutor(max_workers=5) as pool:
        for offset in range(0,len(symbols),5):
            if monotonic()-started > 20:
                failed.extend(symbols[offset:]);break
            pending = {pool.submit(collect,symbol):symbol for symbol in symbols[offset:offset+5]}
            for future in as_completed(pending):
                symbol = pending[future]
                try:
                    for event in future.result():
                        prior = events.get(event['event_id'])
                        if prior:
                            prior['symbols'] = sorted(set(prior['symbols']+event['symbols']))
                            prior['available_at'] = prior['first_seen_at'] = min(prior['first_seen_at'],event['first_seen_at'])
                        else: events[event['event_id']] = event
                    done += 1
                except Exception:
                    failed.append(symbol)
    return list(events.values()), done, sorted(set(failed))


def install(app, database_request, read_all, authorized):
    from fastapi import Request
    @app.get('/api/jobs/news-sync')
    def sync(request: Request):
        authorized(request)
        prior = database_request('GET','dhanvest_news_runs',params={'select':'failed_symbols','order':'id.desc','limit':1})
        run = database_request('POST','dhanvest_news_runs',body={'status':'running'},prefer='return=representation')[0]
        try:
            symbols = [row['symbol'] for row in read_all('stocks') if re.fullmatch(r'[A-Z0-9][A-Z0-9_.-]{0,24}',row['symbol'])]
            # A deadline must not permanently starve companies late in the list.
            retry = (prior[0].get('failed_symbols') or []) if prior else []
            symbols = [symbol for symbol in retry if symbol in symbols]+symbols
            events, done, failed = capture_symbols(symbols)
            if events:
                database_request('POST','dhanvest_news_events',params={'on_conflict':'event_id'},body=events,
                                 prefer='resolution=ignore-duplicates,return=minimal')
            state = 'partial' if failed else 'complete'
            database_request('PATCH','dhanvest_news_runs',params={'id':'eq.'+str(run['id'])},
                body={'status':state,'finished_at':datetime.now(timezone.utc).isoformat(),
                      'company_count':done,'observed_versions':len(events),'failed_symbols':failed})
            return {'status':state,'company_count':done,'observed_versions':len(events),'failed_symbols':failed}
        except Exception:
            database_request('PATCH','dhanvest_news_runs',params={'id':'eq.'+str(run['id'])},
                body={'status':'failed','finished_at':datetime.now(timezone.utc).isoformat()})
            raise

    @app.get('/api/news/status')
    def status():
        rows = database_request('GET','dhanvest_news_runs',params={'select':'status,started_at,finished_at,company_count,observed_versions','order':'id.desc','limit':1})
        return {'last_run':rows[0] if rows else None,'scope':'DSE announcements; daily prospective capture. Newspaper ingestion pending.'}
