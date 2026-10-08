"""Collect dated exchange financial facts separately from legacy records."""
import argparse,json,time
from pathlib import Path
from frontend.api.index import read_all
from frontend.fundamentals import fetch_company,normalize_company

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='data/fundamentals-20261008')
    args=parser.parse_args();folder=Path(args.folder);folder.mkdir(parents=True,exist_ok=True)
    records=[];failed=[];profiles=[]
    for stock in read_all('stocks'):
        target=folder/(stock['symbol']+'.json')
        try:
            if target.exists():data=json.loads(target.read_text(encoding='utf-8'))
            else:
                payload=fetch_company(stock['symbol']);data={'records':normalize_company(payload,stock['id']),
                   'profile':{'id':stock['id'],'symbol':stock['symbol'],'name':payload['name'],'sector':payload['sector'],
                              'statement_url':payload.get('financialStatementsUrl'),'year_end':payload['yearEnd'],
                              'interim':payload.get('interimFinancials')}}
                with target.open('x',encoding='utf-8') as output:json.dump(data,output,ensure_ascii=False)
            records.extend(data['records']);profiles.append(data['profile'])
            print(stock['symbol'],len(data['records']),'annual records',flush=True)
        except Exception as error:failed.append({'symbol':stock['symbol'],'error':type(error).__name__});print(stock['symbol'],'FAILED',type(error).__name__,flush=True)
        time.sleep(.25)
    for name,value in [('records.json',records),('profiles.json',profiles),('manifest.json',{'records':len(records),'companies':len(profiles),'failed':failed})]:
        (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved',len(records),'records; failures:',len(failed),flush=True)

if __name__=='__main__':main()
