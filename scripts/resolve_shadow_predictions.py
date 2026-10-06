"""Resolve research-only forecasts using verified future trading sessions."""
from datetime import datetime,timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from frontend.api.index import read_all,database_request

def outcome(prediction, history):
    today=datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Dhaka')).date().isoformat()
    rows=sorted((row for row in history if row.get('source_verified') is True and row.get('source_url')
                 and prediction['base_date']<row['date']<=today),key=lambda row:row['date'])
    # Duplicate session dates are ambiguous; never count them as extra sessions.
    if len({row['date'] for row in rows})!=len(rows):raise ValueError('Duplicate verified session dates')
    horizon=prediction['horizon_sessions']
    if len(rows)<horizon:return None
    row=rows[horizon-1];price=Decimal(str(row['close_price']));base=Decimal(str(prediction['base_price']))
    if price<=0 or base<=0:raise ValueError('Invalid outcome price')
    return {'prediction_id':prediction['id'],'outcome_date':row['date'],'outcome_price':float(price),
            'return_fraction':float(price/base-1),'actual_direction':'up' if price>base else 'down' if price<base else 'flat',
            'source_url':row['source_url']}

def main():
    resolved={row['prediction_id'] for row in read_all('dhanvest_shadow_outcomes',order='prediction_id.asc')}
    predictions=[row for row in read_all('dhanvest_shadow_predictions',order='id.asc') if row['id'] not in resolved]
    saved=0
    for prediction in predictions:
        history=read_all('market_history',stock_id='eq.'+str(prediction['stock_id']))
        value=outcome(prediction,history)
        if value:
            database_request('POST','dhanvest_shadow_outcomes',params={'on_conflict':'prediction_id'},body=value,
                             prefer='resolution=ignore-duplicates,return=minimal');saved+=1
    print(f'Resolved {saved} research-only outcomes. No public predictions or trading signals enabled.')

if __name__=='__main__':main()
