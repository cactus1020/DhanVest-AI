"""Synthetic UI fixture only; never deployed or imported by production."""
from datetime import date

import pandas as pd
import uvicorn

from frontend.api import index as api
from frontend.research import score_universe


def synthetic_data():
    today = date.today()
    days = pd.date_range(end=today.isoformat(), periods=61, freq=pd.offsets.CustomBusinessDay(weekmask='Sun Mon Tue Wed Thu'))
    stocks = [{'id': i, 'symbol': 'TEST' + str(i), 'name': 'Synthetic test company ' + str(i), 'sector': 'Bank'} for i in range(1, 5)]
    rows = []
    for stock in stocks:
        for i, day in enumerate(days):
            row = {'stock_id': stock['id'], 'date': day.date().isoformat(), 'close_price': 100 + i * .1,
                   'volume': 100000, 'source_url': 'https://example.org/synthetic-fixture', 'source_verified': True}
            if stock['id'] < 4:
                row.update(pe_ratio=10 + stock['id'], roe=20, debt_to_equity=.5, fundamentals_date=days[-1].date().isoformat())
            rows.append(row)
    return stocks, rows, today

def synthetic_stocks():
    stocks, rows, today = synthetic_data()
    return score_universe(stocks, rows, today)


def unavailable_database(*args, **kwargs):
    raise api.DatabaseUnavailable('synthetic_fixture', 'Synthetic UI fixture: database writes are disabled.')


if __name__ == '__main__':
    api.current_stocks = synthetic_stocks
    def synthetic_history(stock_id):
        _, rows, _ = synthetic_data()
        points = api.verified_history([row for row in rows if row['stock_id'] == stock_id])
        return {'points': [{'date':row['date'], 'close':row['close_price']} for row in points]}
    # Replace the route handler for read-only synthetic chart testing.
    for route in api.app.routes:
        if getattr(route, 'path', '') == '/api/stocks/{stock_id}/history':
            route.dependant.call = synthetic_history
    # No paid AI calls or production waitlist writes in browser tests.
    api.generated_explanation = lambda stock: (api.explain_bangla(stock), 'rules')
    api.database_request = unavailable_database
    uvicorn.run(api.app, host='127.0.0.1', port=8001)
