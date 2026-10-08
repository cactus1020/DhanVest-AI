"""Collect public headline/date/URL metadata, not full newspaper articles."""
import argparse,hashlib,json,re,time
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

BASE='https://today.thefinancialexpress.com.bd'
SECTORS={'Bank':['bank','banking'],'Insurance':['insurance','insurer'],
 'Textile':['textile','garment','rmg','apparel','denim','spinning'],
 'PharmaChem':['pharma','pharmaceutical','drug','chemical'],
 'FuelPower':['power','electricity','energy','gas'],'Engineering':['engineering','steel','cement'],
 'Telecom':['telecom','mobile operator'],'Financial In':['leasing','nbfi','non-bank'],
 'FoodAllied':['sugar','food','tobacco'],'Misc':[]}
ALIASES={'GP':['grameenphone'],'SQURPHARMA':['square pharmaceuticals'],'BXPHARMA':['beximco pharmaceuticals'],
 'BATBC':['bat bangladesh','british american tobacco','batb'],'UPGDCL':['united power'],
 'BRACBANK':['brac bank'],'ACMEPL':['acme pesticides'],'ARGONDENIM':['argon denim','argon denims']}

def company_aliases(profile):
    name=re.sub(r'\b(?:limited|ltd\.?|plc\.?|corporation)\b','',profile['name'],flags=re.I).strip(' .')
    aliases=[profile['symbol'],name,re.sub(r'^the\s+','',name,flags=re.I),*ALIASES.get(profile['symbol'],[])]
    if profile['symbol'].endswith('BANK'):aliases.append(profile['symbol'][:-4]+' Bank')
    return aliases

def matches(title,profiles,outside_patterns=()):
    direct=[];sector=[];reasons={}
    for p in profiles:
        aliases=[a for a in company_aliases(p) if len(a)>2 or a==p['symbol']]
        hit=next((a for a in aliases if re.search(r'(?<!\w)'+re.escape(a)+r'(?!\w)',title,re.I)),None)
        if hit:direct.append(p['symbol']);reasons[p['symbol']]='company:'+hit
    # Sector-only headlines apply to that sector; explicit company headlines
    # stay company-specific rather than becoming every bank's news.
    if not direct:
        if any(pattern.search(title) for pattern in outside_patterns):return [],{}
        for p in profiles:
            hit=next((term for term in SECTORS.get(p['sector'],[]) if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',title,re.I)),None)
            if hit:sector.append(p['symbol']);reasons[p['symbol']]='sector:'+hit
    return sorted(set(direct or sector)),reasons

def parse_archive(html,day,profiles,observed):
    soup=BeautifulSoup(html,'html.parser')
    requested=day.strftime('%d-%m-%Y')
    if 'Search date: '+requested not in soup.get_text(' ',strip=True):raise ValueError('Archive did not confirm requested publication date')
    events={}
    for heading in soup.select('h2'):
        title=heading.get_text(' ',strip=True)
        link=heading.find_next('a',href=True)
        if not link:continue
        url=link['href'];parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname!='today.thefinancialexpress.com.bd' or not parsed.path.startswith('/stock-corporate/'):continue
        if len(title)>1000:continue
        symbols,reasons=matches(title,profiles)
        if not symbols:continue
        available=datetime.combine(day+timedelta(days=1),datetime.min.time()).replace(tzinfo=__import__('zoneinfo').ZoneInfo('Asia/Dhaka')).isoformat()
        identity=hashlib.sha256(url.encode()).hexdigest()
        events[identity]={'event_id':identity,'title':title,'symbols':symbols,'kind':'report','source_url':url,
            'published_date':day.isoformat(),'available_at':available,'availability_basis':'archive_reconstruction',
            'first_seen_at':observed,'mapping_reasons':reasons,'publisher':'The Financial Express',
            'content_scope':'headline_metadata_only',
            'positive_keyword_count':len(re.findall(r'\b(?:rise|growth|increase|profit|dividend|expansion)\b',title,re.I)),
            'negative_keyword_count':len(re.findall(r'\b(?:fall|drop|loss|decline|penalty|default)\b',title,re.I))}
    return list(events.values())

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profiles',required=True)
    p.add_argument('--start',default='2024-10-06');p.add_argument('--end',default='2026-10-06')
    p.add_argument('--folder',default='data/newspaper-archive-20261008');a=p.parse_args()
    profiles=json.loads(Path(a.profiles).read_text(encoding='utf-8'));start=date.fromisoformat(a.start);end=date.fromisoformat(a.end)
    folder=Path(a.folder);folder.mkdir(parents=True,exist_ok=True);events={};failed=[];days=0
    with httpx.Client(timeout=httpx.Timeout(20,connect=5),follow_redirects=True,headers={'User-Agent':'DhanVest research metadata collector'}) as client:
        # This publisher returns its HTML site at /robots.txt, not a robots file.
        # If a valid robots file appears, honor it before requesting archive pages.
        robots=client.get(BASE+'/robots.txt')
        if robots.status_code==200 and '<html' not in robots.text[:1000].lower():
            from urllib.robotparser import RobotFileParser
            rules=RobotFileParser();rules.parse(robots.text.splitlines())
            if not rules.can_fetch('*',BASE+'/stock-corporate'):raise ValueError('Archive crawling disallowed by publisher robots rules')
        day=start
        while day<=end:
            target=folder/(day.isoformat()+'.json')
            try:
                if target.exists():items=json.loads(target.read_text(encoding='utf-8'))
                else:
                    r=client.get(BASE+'/stock-corporate',params={'date':day.strftime('%d-%m-%Y')});r.raise_for_status()
                    items=parse_archive(r.text,day,profiles,datetime.now(timezone.utc).isoformat())
                    with target.open('x',encoding='utf-8') as output:json.dump(items,output,ensure_ascii=False)
                for event in items:
                    previous=events.get(event['event_id'])
                    if not previous or event['published_date']<previous['published_date']:events[event['event_id']]=event
                days+=1
            except Exception as error:failed.append({'day':day.isoformat(),'error':type(error).__name__})
            if days%25==0:print(day.isoformat(),'days',days,'matched headlines',len(events),'failures',len(failed),flush=True)
            time.sleep(.35);day+=timedelta(days=1)
    with (folder/'events.jsonl').open('w',encoding='utf-8') as output:
        for event in sorted(events.values(),key=lambda x:x['available_at']):output.write(json.dumps(event,ensure_ascii=False)+'\n')
    (folder/'manifest.json').write_text(json.dumps({'publisher':'The Financial Express','start':a.start,'end':a.end,'days':days,'events':len(events),'failures':failed,
      'limitations':['Title metadata only, not full articles or validated sentiment.','Historical availability conservatively reconstructed; archive revisions are unknown.','Current-universe selection bias and sector-mapping noise remain.','Commercial publisher data rights are not established.']},indent=2),encoding='utf-8')
    print('Finished:',days,'archive days;',len(events),'events;',len(failed),'failures',flush=True)

if __name__=='__main__':main()
