"""Dated company facts; missing debt/equity is never treated as zero."""
import calendar
import hashlib
import json
import re
from datetime import date, datetime, timezone
import httpx

DSE = 'https://www.dse.com.bd'

def company_payload(html, symbol):
    chunks = []
    for raw in re.findall(r'self\.__next_f\.push\((\[.*?\])\)</script>', html):
        entry = json.loads(raw)
        if len(entry)>1 and isinstance(entry[1],str): chunks.append(entry[1])
    stream = ''.join(chunks)
    needle = '{"code":'+json.dumps(symbol)
    positions = [match.start() for match in re.finditer(re.escape(needle),stream)]
    for at in positions:
        try: payload = json.JSONDecoder().raw_decode(stream,at)[0]
        except ValueError: continue
        if payload.get('code')==symbol and 'multiYearFinancials' in payload:
            return payload
    raise ValueError('DSE company financial payload not found')

def fiscal_end(year, month):
    month_number = list(calendar.month_name).index(month)
    if not month_number: raise ValueError('Unknown fiscal year end')
    return date(int(year),month_number,calendar.monthrange(int(year),month_number)[1]).isoformat()

def fetch_company(symbol):
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_.-]{0,24}',symbol): raise ValueError('Invalid company symbol')
    with httpx.Client(timeout=httpx.Timeout(20,connect=5),follow_redirects=True) as client:
        response = client.get(DSE+'/company/'+symbol)
        response.raise_for_status()
    return company_payload(response.text,symbol)

def normalize_company(payload, stock_id):
    today = datetime.now(timezone.utc).date()
    records=[]
    for item in payload.get('multiYearFinancials') or []:
        period = fiscal_end(item['year'],payload['yearEnd'])
        if date.fromisoformat(period)>today: continue
        eps = item.get('epsBasic'); nav=item.get('nav')
        if eps is None and nav is None:continue
        record={'stock_id':stock_id,'symbol':payload['code'],'company_name':payload['name'],
            'sector':payload['sector'],'period_end':period,'period_kind':'annual',
            'eps':eps,'nav_per_share':nav,'net_profit_mn':item.get('profit'),
            'roe':None,'debt_to_equity':None,'roe_method':None,'debt_method':None,
            'source_url':DSE+'/company/'+payload['code'],'source_verified':True,
            'source_observed_at':datetime.now(timezone.utc).isoformat(),
            'availability_basis':'observed_current_snapshot',
            'notes':['Annual values reported by the exchange. Publication/revision timestamps are not established for historical backtesting.',
                     'Unspecified loan date or missing long-term debt cannot establish debt/equity.']}
        signature = {k:v for k,v in record.items() if k not in ('source_observed_at','notes')}
        record['record_id']=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        record.update(benchmark_price=None,price_date=None)
        records.append(record)
    return records

def attach_fundamentals(stocks, market_rows, records, today=None):
    """Enrich today's research view only; do not rewrite historical market rows."""
    today=today or date.today();selected={}
    for item in records:
        if item.get('source_verified') is not True:continue
        try: end=date.fromisoformat(item['period_end'])
        except (KeyError,TypeError,ValueError):continue
        if end>today:continue
        prior=selected.get(item['stock_id'])
        if not prior or (item['period_end'],bool(item.get('roe_method')),item.get('source_observed_at','')) > (prior['period_end'],bool(prior.get('roe_method')),prior.get('source_observed_at','')):
            selected[item['stock_id']]=item
    enriched_stocks=[];enriched_rows=[dict(row) for row in market_rows]
    latest={}
    for i,row in enumerate(enriched_rows):
        if row.get('source_verified') is True and (row['stock_id'] not in latest or row['date']>enriched_rows[latest[row['stock_id']]]['date']):latest[row['stock_id']]=i
    for stock in stocks:
        info=selected.get(stock['id']);updated=dict(stock)
        if info:
            updated.update(sector=info['sector'],name=info['company_name'])
            if stock['id'] in latest:
                row=enriched_rows[latest[stock['id']]]
                eps=info.get('eps')
                row.update(fundamentals_date=info['period_end'],fundamentals_period_kind=info['period_kind'],
                           roe=info.get('roe'),debt_to_equity=info.get('debt_to_equity'),
                           pe_ratio=row['close_price']/eps if eps and eps>0 else None,
                           fundamentals=info)
        enriched_stocks.append(updated)
    return enriched_stocks,enriched_rows,selected
