"""Research price-plus-news comparison. Outputs are not deployed signals."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score,balanced_accuracy_score,brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from backend.data_validation import load_market_data,validate_source
from backend.train_model import features,chronological_folds

NUMERIC=['return_daily','momentum_ratio','vol_ma5']

def attach_news(frame,events,horizon):
    prepared=[]
    for event in events:
        available=pd.Timestamp(event['available_at'])
        if available.tzinfo is None:raise ValueError('News availability timestamps need a timezone.')
        prepared.append((event,available.tz_convert('UTC')))
    result=[]
    for symbol,group in frame.groupby('symbol'):
        group=group.sort_values('date').copy()
        group['label_date']=group['date'].shift(-horizon)
        group['target']=(group['close'].shift(-horizon)>group['close']).astype(int)
        texts=[];counts=[];positive=[];negative=[]
        relevant=[(event,available) for event,available in prepared if symbol in event['symbols']]
        for day in group['date']:
            # Decision cutoff is 14:30 Dhaka. Date-only archives become usable next day.
            cutoff=pd.Timestamp(day).tz_localize('Asia/Dhaka')+pd.Timedelta(hours=14,minutes=30)
            cutoff=cutoff.tz_convert('UTC');start=cutoff-pd.Timedelta(days=7)
            eligible={event['event_id']:event for event,available in relevant if start<available<=cutoff}
            texts.append(' '.join(event['title'] for event in eligible.values()) or '__no_news__')
            counts.append(len(eligible));positive.append(sum(event.get('positive_keyword_count',0) for event in eligible.values()));negative.append(sum(event.get('negative_keyword_count',0) for event in eligible.values()))
        group['news_text']=texts;group['news_count']=counts;group['news_positive_terms']=positive;group['news_negative_terms']=negative;result.append(group)
    return pd.concat(result).dropna(subset=['label_date'])

def classifier(with_news):
    numeric=NUMERIC+(['news_count','news_positive_terms','news_negative_terms'] if with_news else [])
    transforms=[('numeric',Pipeline([('impute',SimpleImputer()),('scale',StandardScaler())]),numeric)]
    if with_news:transforms.append(('news',TfidfVectorizer(max_features=2000,ngram_range=(1,2),min_df=2,token_pattern=r'(?u)\b\w+\b'),'news_text'))
    return Pipeline([('inputs',ColumnTransformer(transforms)),('model',LogisticRegression(max_iter=1000,class_weight='balanced',random_state=42))])

def evaluate(price_csv,news_jsonl,source_url,horizons=(2,40),output='data/news-model-evaluation.json',allow_archive_reconstruction=False, special_sessions=()):
    validate_source(source_url)
    prices=features(load_market_data(price_csv,special_sessions=special_sessions))
    events=[json.loads(line) for line in Path(news_jsonl).read_text(encoding='utf-8').splitlines() if line.strip()]
    if not events:raise ValueError('News dataset is empty.')
    if not allow_archive_reconstruction and any(event.get('availability_basis')=='archive_reconstruction' for event in events):
        raise ValueError('Archive timestamps require explicit research-only acknowledgement; they do not establish live point-in-time availability.')
    report={'status':'research_only','source_url':source_url,'news_events':len(events),'horizons':{},'limitations':['Current-universe selection/survivorship bias.','Unadjusted source prices may contain corporate-action effects.','Publication/archive revision metadata is incomplete.','These are exploratory folds, not a final untouched holdout or calibrated production probabilities.']}
    for horizon in horizons:
        frame=attach_news(prices,events,horizon)
        folds=[]
        for train,test in chronological_folds(frame):
            if train['target'].nunique()<2:continue
            row={'test_start':test['date'].min().date().isoformat(),'test_end':test['date'].max().date().isoformat(),'train_rows':len(train),'test_rows':len(test),'latest_training_label':train['label_date'].max().date().isoformat(),'test_rows_with_news':int((test['news_count']>0).sum())}
            for label,include in [('price_only',False),('price_plus_news',True)]:
                model=classifier(include);model.fit(train,train['target']);prediction=model.predict(test);prob=model.predict_proba(test)[:,1]
                row[label]={'accuracy':float(accuracy_score(test['target'],prediction)),'balanced_accuracy':float(balanced_accuracy_score(test['target'],prediction)),'brier_score':float(brier_score_loss(test['target'],prob))}
            majority=int(train['target'].mode().iloc[0]);row['majority_baseline_accuracy']=float(accuracy_score(test['target'],np.full(len(test),majority)));folds.append(row)
        report['horizons'][str(horizon)+'_trading_sessions']=folds
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('prices');parser.add_argument('news');parser.add_argument('--source-url',required=True);parser.add_argument('--allow-archive-reconstruction',action='store_true');parser.add_argument('--output',default='data/news-model-evaluation.json');args=parser.parse_args()
    report=evaluate(args.prices,args.news,args.source_url,output=args.output,allow_archive_reconstruction=args.allow_archive_reconstruction)
    print('Price-only and news-augmented research comparisons saved; no production forecasts enabled.')
