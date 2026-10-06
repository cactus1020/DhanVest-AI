import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from frontend.api import index as api

class HistoryApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_unverified_legacy_prices_are_never_charted(self):
        with patch.object(api, 'database_request', return_value=[{'id': 1}]), patch.object(api, 'read_all', return_value=[{'date':'2026-01-01','close_price':100,'volume':1}]):
            response = self.client.get('/api/stocks/1/history')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['points'], [])

    def test_verified_prices_are_sorted_and_future_rows_excluded(self):
        rows = [{'date': d, 'close_price': p, 'volume': 1, 'source_verified': True, 'source_url':'https://example.org/data'} for d,p in [('2026-01-02',12),('2099-01-01',999),('2026-01-01',10)]]
        with patch.object(api, 'database_request', return_value=[{'id': 1}]), patch.object(api, 'read_all', return_value=rows) as reader:
            response = self.client.get('/api/stocks/1/history')
        self.assertEqual(response.json()['points'], [{'date':'2026-01-01','close':10.0},{'date':'2026-01-02','close':12.0}])
        reader.assert_any_call('daily_data', stock_id='eq.1')

    def test_unknown_stock_and_invalid_identifier(self):
        with patch.object(api, 'database_request', return_value=[]):
            self.assertEqual(self.client.get('/api/stocks/999/history').status_code,404)
        self.assertEqual(self.client.get('/api/stocks/invalid/history').status_code,422)


class StoredResearchTests(unittest.TestCase):
    def test_preserved_data_and_scores_do_not_become_verified_scores(self):
        from frontend.research import score_universe, add_stored_research, explain_stored_bangla
        stocks = [{'id':1,'symbol':'TEST','name':'Test','sector':'General'}]
        rows = [{'id':2,'stock_id':1,'date':'2026-01-02','close_price':110,'volume':20}, {'id':1,'stock_id':1,'date':'2026-01-01','close_price':100,'volume':10}]
        result = add_stored_research(score_universe(stocks,rows),rows,[{'stock_id':1,'composite_score':75,'quality_score':50}])[0]
        self.assertIsNone(result['composite'])
        self.assertEqual(result['coverage'],0)
        self.assertEqual(result['saved_scores']['composite'],75)
        self.assertEqual(result['stored_data']['close'],110)
        self.assertEqual(result['stored_data']['change_percent'],10)
        self.assertFalse(result['stored_data']['dates_verified'])
        self.assertIn('110.00',explain_stored_bangla(result))

    def test_stored_chart_uses_observations_not_invented_dates(self):
        client = TestClient(api.app)
        rows = [{'id':1,'date':'2026-01-01','close_price':100,'volume':10}]
        with patch.object(api,'database_request',return_value=[{'id':1}]), patch.object(api,'read_all',return_value=rows):
            data = client.get('/api/stocks/1/history?include_stored=true').json()
        self.assertEqual(data['mode'],'stored_sequence')
        self.assertEqual(data['points'],[{'observation':1,'close':100.0}])
        self.assertIsNone(data['source_url'])

    def test_legacy_explanation_never_calls_ai(self):
        stock = {'id':1,'name':'Test','coverage':0,'as_of':None,'stored_data':{'count':2,'close':110,'change_percent':10,'volume':20,'pe_ratio':None,'roe':None,'debt_to_equity':None},'saved_scores':None}
        with patch.object(api,'current_stocks',return_value=[stock]), patch.object(api,'generated_explanation') as generator:
            response = TestClient(api.app).post('/api/explain',json={'stock_id':1})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['method'],'stored_records')
        generator.assert_not_called()

    def test_v2_route_and_original_route_coexist(self):
        client = TestClient(api.app)
        self.assertIn('DHANVEST V2',client.get('/v2').text)
        self.assertEqual(client.get('/research').status_code,200)
        self.assertEqual(client.get('/dashboard.html').status_code,200)
