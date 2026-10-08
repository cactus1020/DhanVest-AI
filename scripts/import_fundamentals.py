"""Validate all financial facts before inserting immutable versions."""
import argparse,json,math
from datetime import date,datetime
from pathlib import Path
from urllib.parse import urlparse
from frontend.api.index import database_request

def validate(records):
    ids=set()
    for row in records:
        if row['record_id'] in ids:raise ValueError('Duplicate financial version')
        ids.add(row['record_id'])
        if date.fromisoformat(row['period_end'])>date.today():raise ValueError('Future reporting period')
        if datetime.fromisoformat(row['source_observed_at']).tzinfo is None:raise ValueError('Observation needs timezone')
        source=urlparse(row['source_url'])
        if source.scheme!='https' or not source.hostname or source.username or source.password or row['source_verified'] is not True:raise ValueError('Invalid financial source')
        for field in ['eps','nav_per_share','net_profit_mn','roe','debt_to_equity','benchmark_price']:
            value=row.get(field)
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):raise ValueError('Invalid number: '+field)
        if row.get('debt_to_equity') is not None and (row['debt_to_equity']<0 or not row.get('debt_method')):raise ValueError('Debt ratio needs reviewed definition')
        if row.get('roe') is not None and not row.get('roe_method'):raise ValueError('ROE needs reviewed definition')
    return records

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');a=p.parse_args()
    records=validate(json.loads(Path(a.input).read_text(encoding='utf-8')))
    keys=set().union(*(row.keys() for row in records))
    records=[{key:row.get(key) for key in keys} for row in records]
    for offset in range(0,len(records),100):
        database_request('POST','dhanvest_fundamentals',params={'on_conflict':'record_id'},body=records[offset:offset+100],prefer='resolution=ignore-duplicates,return=minimal')
    print('Imported',len(records),'financial versions; old market rows and saved scores untouched.')

if __name__=='__main__':main()
