"""Read-only DSE public market adapter. No credentials or database writes."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from threading import RLock
from time import monotonic
from urllib.parse import urlencode
import httpx
try:
    from .research import number
except ImportError:
    from research import number

BASE = 'https://www.dsebd.org'
_cache = {}
_lock = RLock()

class FeedUnavailable(Exception):
    pass

def fetch_json(path, params=None, ttl=60):
    cache_key = (path, tuple(sorted((params or {}).items())))
    with _lock:
        cached = _cache.get(cache_key)
        if cached and monotonic() - cached[0] < ttl:
            return cached[1]
    try:
        with httpx.Client(timeout=httpx.Timeout(12, connect=5), follow_redirects=True) as client:
            response = client.get(BASE + path, params=params)
            response.raise_for_status()
            value = response.json()
        if not isinstance(value, dict):
            raise ValueError('Invalid feed structure')
    except (httpx.HTTPError, ValueError):
        raise FeedUnavailable('The DSE source is temporarily unavailable. Stored research remains available.') from None
    value['_retrieved_at'] = datetime.now(timezone.utc).isoformat()
    with _lock:
        # Bound per-instance cache even when many company symbols are requested.
        if len(_cache) >= 256:
            _cache.pop(next(iter(_cache)))
        _cache[cache_key] = (monotonic(), value)
    return value

def valid_session(payload):
    session = payload.get('session')
    if not isinstance(session, dict):
        raise FeedUnavailable('The DSE source did not provide a market session date.')
    try:
        day = date.fromisoformat(session['sessionDate'])
    except (KeyError, ValueError, TypeError):
        raise FeedUnavailable('The DSE market session date is invalid.') from None
    if day > datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Dhaka')).date():
        raise FeedUnavailable('The source returned a future market session.')
    return session

def parse_prices(payload):
    session = valid_session(payload)
    cols = payload.get('cols', [])
    if not isinstance(cols, list) or not {'code','board','assetType','ltp','ycp','volume','close'}.issubset(cols):
        raise FeedUnavailable('DSE price fields have changed. Stored research remains available.')
    rows = payload.get('rows')
    if not isinstance(rows, list):
        raise FeedUnavailable('Invalid DSE price records.')
    quotes = {}
    for values in rows:
        if not isinstance(values, list) or len(values) != len(cols):
            raise FeedUnavailable('Invalid DSE price row.')
        row = dict(zip(cols, values))
        if row['board'] != 'PUBLIC' or row['assetType'] != 'EQ':
            continue
        symbol = row['code']
        if not isinstance(symbol, str) or not symbol or symbol in quotes:
            raise FeedUnavailable('Duplicate or invalid DSE stock code.')
        ltp, prior = number(row['ltp'],0), number(row['ycp'],0)
        volume = number(row['volume'],0)
        if volume is None or not volume.is_integer():
            raise FeedUnavailable('Invalid DSE trading volume.')
        traded = ltp is not None and ltp > 0 and volume > 0
        close = number(row['close'],0)
        quotes[symbol] = {'symbol':symbol, 'price':ltp if traded else None, 'close':close if close and close > 0 else None,
            'previous_close':prior if prior and prior > 0 else None,
            'change_percent':round((ltp/prior-1)*100,2) if traded and prior and prior > 0 else None,
            'volume':int(volume), 'traded':traded, 'sector':str(row.get('sector') or 'Unknown'),
            'high':number(row.get('high'),0), 'low':number(row.get('low'),0),
            'session_date':session['sessionDate']}
    if not quotes:
        raise FeedUnavailable('DSE returned no equity quotes.')
    return list(quotes.values()), session

def market_snapshot():
    prices = fetch_json('/api/live/prices')
    quotes, session = parse_prices(prices)
    market = fetch_json('/api/live/market')
    other_session = valid_session(market)
    if other_session['sessionDate'] != session['sessionDate']:
        raise FeedUnavailable('DSE source sessions do not match. Please retry.')
    return {'quotes':quotes, 'session':session, 'indices':market.get('indices',[]),
            'breadth':market.get('breadth',{}), 'source_updated_at':market.get('totals',{}).get('tradeTime'),
            'retrieved_at':prices['_retrieved_at'],
            'source_url':BASE + '/api/live/prices', 'source':'DSE public website',
            'delivery':'Public website snapshot; exchange latency is not guaranteed.'}

def company_history(symbol, start, end):
    data = fetch_json('/api/live/data-archive/day-end', {'inst':symbol,'from':start,'to':end}, ttl=300)
    rows = data.get('rows')
    if not isinstance(rows,list):
        raise FeedUnavailable('Invalid DSE historical response.')
    if data.get('truncated') or (data.get('total') or 0) > len(rows):
        raise FeedUnavailable('DSE historical response is incomplete; request a smaller date range.')
    points = {}
    excluded_dates = 0
    for row in rows:
        try:
            day = date.fromisoformat(row['date'])
            price = number(row['closep'],0)
            volume = number(row['volume'],0)
            if not start <= day.isoformat() <= end:
                excluded_dates += 1
                continue
            valid = row['tradingCode']==symbol and day <= date.today() and price and price>0 and volume is not None and volume>=0 and volume.is_integer()
        except (KeyError,ValueError,TypeError):
            valid = False
        if not valid or day.isoformat() in points:
            raise FeedUnavailable('DSE historical records failed validation.')
        points[day.isoformat()] = {'date':day.isoformat(),'close':price,'volume':int(volume),
            'open':number(row.get('openp'),0),'high':number(row.get('high'),0),'low':number(row.get('low'),0)}
    return {'points':[points[key] for key in sorted(points)], 'mode':'dse_history',
            'source_url':BASE+'/api/live/data-archive/day-end?'+urlencode({'inst':symbol,'from':start,'to':end}),
            'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'excluded_out_of_range':excluded_dates,
            'adjustment':'Source prices; corporate-action adjustment has not been established.'}

def company_news(symbol):
    data = fetch_json('/api/live/news',{'code':symbol},ttl=300)
    rows = data.get('rows')
    if not isinstance(rows,list):
        raise FeedUnavailable('Invalid DSE announcement response.')
    items=[]
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or row.get('code') != symbol:
            continue
        identity=str(row.get('id') or '')
        title=row.get('summary')
        if not identity or identity in seen or not isinstance(title,str):
            continue
        seen.add(identity)
        items.append({'id':identity,'symbol':symbol,'title':title[:300], 'filed_at':row.get('filedAt'),
            'kind':row.get('type') or 'Announcement', 'source_url':BASE+'/api/live/news?'+urlencode({'code':symbol}),
            'verification':'Published by the exchange; company claims are not independently verified.'})
    return {'items':items[:20],'truncated':bool(data.get('truncated')), 'source':'DSE company announcements',
            'retrieved_at':datetime.now(timezone.utc).isoformat()}
