"""Combine exchange facts with individually reviewed official report ratios."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from frontend.fundamentals import fetch_company,normalize_company

ROOT=Path('data/fundamentals-20261008')
GP_REPORT='https://cdn01da.grameenphone.com/sites/default/files/2026-03/Annual%20Report%202025%20of%20GP.pdf#page=100'
BAT_REPORT='https://www.batbangladesh.com/content/dam/endmarkets/bd/en/download/investors-and-reporting/financial-statements/2026/Annual_Report_2025.pdf#page=65'

def main():
    records=json.loads((ROOT/'records.json').read_text(encoding='utf-8'))
    # Visually checked PDF page 100 (printed 98), 2025 column; do not infer
    # these reported ratios from current share count or undated loan amounts.
    gp=next(row for row in records if row['symbol']=='GP' and row['period_end']=='2025-12-31')
    reviewed=dict(gp,roe=49.0,debt_to_equity=1.21,roe_method='Reported annual ROE (%)',
      debt_method='Reported annual debt/equity ratio; issuer definition',source_url=GP_REPORT,
      source_observed_at=datetime.now(timezone.utc).isoformat(),
      notes=['Official annual report, PDF page 100 / printed page 98, Table 1, 2025 column.',
             'Annual ratios measure the reporting year, not current-quarter financial health.',
             'Debt/equity definitions can differ by issuer; this is a heuristic comparison.'])
    signature={k:v for k,v in reviewed.items() if k not in ('record_id','source_observed_at')}
    reviewed['record_id']=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest();records.append(reviewed)
    bat=next(row for row in records if row['symbol']=='BATBC' and row['period_end']=='2025-12-31')
    reviewed=dict(bat,roe=10.55,debt_to_equity=0.1762,roe_method='Reported annual ROE (%)',
      debt_method='Reported Debt Equity Ratio (%) divided by 100',source_url=BAT_REPORT,
      source_observed_at=datetime.now(timezone.utc).isoformat(),
      notes=['Official annual report, PDF page 65 / printed page 63, Financial Highlights, 2025 column.',
             'Reported debt/equity is 17.62 percent, converted to 0.1762 times.',
             'Annual ratios measure the reporting year, not current-quarter financial health.'])
    signature={k:v for k,v in reviewed.items() if k not in ('record_id','source_observed_at')}
    reviewed['record_id']=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest();records.append(reviewed)
    # Supplemental sector peer: no new stock, prices or legacy rows inserted.
    peer=fetch_company('BSCPLC');peer_rows=normalize_company(peer,None)
    if peer_rows:
        latest=max(peer_rows,key=lambda r:r['period_end'])
        latest.update(benchmark_price=peer['price'],price_date=peer['asOfDate'])
        signature={k:v for k,v in latest.items() if k not in ('record_id','source_observed_at')}
        latest['record_id']=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest();records.append(latest)
    target=ROOT/'import-records-reviewed.json'
    with target.open('x',encoding='utf-8') as output:json.dump(records,output,ensure_ascii=False,indent=2)
    print('Prepared',len(records),'sourced records including reviewed GP ratios and one supplemental Telecom peer.')

if __name__=='__main__':main()
