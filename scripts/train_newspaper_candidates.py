"""Reproducible offline price + disclosures + newspaper-headline experiment."""
import argparse,hashlib,json,pickle,re
from datetime import datetime,timezone
from pathlib import Path
from backend.data_validation import load_market_data
from backend.train_model import features
from backend.train_news_model import evaluate,attach_news,classifier

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prices',default='data/dse-history-20261006/dated-prices.csv')
    p.add_argument('--official-news',default='data/dse-news-20261006/events.jsonl')
    p.add_argument('--newspaper-news',default='data/newspaper-archive-20261008/events.jsonl')
    p.add_argument('--folder',default='data/newspaper-model-20261008');a=p.parse_args()
    folder=Path(a.folder);folder.mkdir(parents=True,exist_ok=True);events={};newspaper=0
    for name in [a.official_news,a.newspaper_news]:
        for line in Path(name).read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            event=json.loads(line)
            if event.get('kind')=='report':
                event['positive_keyword_count']=len(re.findall(r'\b(?:rise|growth|increase|profit|dividend|expansion)\b',event['title'],re.I))
                event['negative_keyword_count']=len(re.findall(r'\b(?:fall|drop|loss|decline|penalty|default)\b',event['title'],re.I))
            if event['event_id'] in events:continue
            events[event['event_id']]=event
            if event.get('kind')=='report':newspaper+=1
    combined=folder/'combined-events.jsonl'
    with combined.open('x',encoding='utf-8') as output:
        for event in events.values():output.write(json.dumps(event,ensure_ascii=False)+'\n')
    special=('2025-05-17','2025-05-24','2026-05-23')
    report=evaluate(a.prices,combined,'https://www.dsebd.org/',output=folder/'evaluation.json',allow_archive_reconstruction=True,special_sessions=special)
    prices=features(load_market_data(a.prices,special_sessions=special),include_labels=False)
    for horizon in (2,40):
        training=attach_news(prices,list(events.values()),horizon)
        model=classifier(True);model.fit(training,training['target'])
        path=folder/f'price-news-{horizon}-sessions.pkl'
        with path.open('xb') as output:pickle.dump(model,output)
        metadata={'status':'research_only_not_production_approved','horizon_sessions':horizon,'training_rows':len(training),
            'decision_cutoff':'16:30 Asia/Dhaka; after close',
            'trained_at':datetime.now(timezone.utc).isoformat(),'price_sha256':hashlib.sha256(Path(a.prices).read_bytes()).hexdigest(),
            'news_sha256':hashlib.sha256(combined.read_bytes()).hexdigest(),'newspaper_headlines':newspaper,'official_events':len(events)-newspaper,
            'latest_training_label':training['label_date'].max().date().isoformat(),'limitations':report['limitations']}
        with path.with_suffix('.json').open('x',encoding='utf-8') as output:json.dump(metadata,output,indent=2)
        print('Saved',horizon,'session research candidate;',len(training),'rows',flush=True)
    print('Trained on',newspaper,'newspaper headlines and',len(events)-newspaper,'official events. Public forecasts remain disabled.',flush=True)

if __name__=='__main__':main()
