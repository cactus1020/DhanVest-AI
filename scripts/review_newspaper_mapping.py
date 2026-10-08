"""Review stored metadata against the official full company catalogue."""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
import httpx
from scripts.collect_newspaper_archive import matches,company_aliases

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',default='data/newspaper-archive-reviewed-20261008')
    p.add_argument('--input',default='data/newspaper-archive-20261008/events.jsonl')
    p.add_argument('--profiles',default='data/fundamentals-20261008/profiles.json')
    p.add_argument('--catalogue',help='Saved catalogue JSON to reproduce a prior entity review')
    args=p.parse_args()
    folder=Path(args.folder);folder.mkdir(parents=True,exist_ok=True)
    source=Path(args.input)
    profiles=json.loads(Path(args.profiles).read_text(encoding='utf-8'))
    if args.catalogue:
        snapshot=json.loads(Path(args.catalogue).read_text(encoding='utf-8'))
        companies=snapshot['companies']
    else:
        companies=fetch_catalogue()
        snapshot={'source_url':'https://www.dse.com.bd/companies','observed_at':datetime.now(timezone.utc).isoformat(),'companies':companies}
    with (folder/'catalogue.json').open('x',encoding='utf-8') as output:json.dump(snapshot,output,ensure_ascii=False,indent=2)
    review(source,profiles,companies,folder)

def fetch_catalogue():
    html=httpx.get('https://www.dse.com.bd/companies',timeout=20).text
    parts=[]
    for raw in re.findall(r'self\.__next_f\.push\((\[.*?\])\)</script>',html):
        value=json.loads(raw)
        if len(value)>1 and isinstance(value[1],str):parts.append(value[1])
    companies={code:name for code,name in re.findall(r'\{"code":"([^"\\]+)","name":"([^"\\]+)"',''.join(parts))}
    if len(companies)<300:raise ValueError('Official catalogue is incomplete')
    return companies

def review(source,profiles,companies,folder):
    covered={p['symbol'] for p in profiles}
    outside=[]
    for code,name in companies.items():
        if code in covered:continue
        for alias in company_aliases({'symbol':code,'name':name}):
            if len(alias)>2:outside.append(re.compile(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',re.I))
    count=0;excluded=0;changed=0
    with (folder/'events.jsonl').open('x',encoding='utf-8') as output:
        for line in source.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            row=json.loads(line);symbols,reasons=matches(row['title'],profiles,outside)
            if not symbols:excluded+=1;continue
            if symbols!=row['symbols']:changed+=1
            row.update(symbols=symbols,mapping_reasons=reasons)
            output.write(json.dumps(row,ensure_ascii=False)+'\n');count+=1
    with (folder/'manifest.json').open('x',encoding='utf-8') as output:
        json.dump({'publisher':'The Financial Express','events':count,'excluded_company_specific_stories_outside_covered_universe':excluded,
                   'changed_mappings':changed,'catalogue_companies':len(companies),'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                   'limitations':['Review refines the collected subset; it does not establish exhaustive newspaper coverage.','Current catalogue/alias mapping still needs entity and historical-name review.']},output,indent=2)
    print('Reviewed',count,'headlines; excluded',excluded,'outside-universe company stories; remapped',changed,flush=True)

if __name__=='__main__':main()
