import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from frontend.api import index as api
from frontend import paper_trading as paper

USER='11111111-1111-4111-8111-111111111111'
REQUEST='22222222-2222-4222-8222-222222222222'
ORDER={'symbol':'GP','side':'buy','quantity':5,'request_id':REQUEST}
AUTH={'Authorization':'Bearer verified-user-token'}

def snapshot(open=True, seconds=0):
    return {'session':{'isOpen':open,'sessionDate':'2026-10-06'},
        'retrieved_at':(datetime.now(timezone.utc)-timedelta(seconds=seconds)).isoformat(),
        'quotes':[{'symbol':'GP','traded':True,'price':250,'session_date':'2026-10-06'}]}

class PaperTradingTests(unittest.TestCase):
    def setUp(self): self.client=TestClient(api.app)

    def test_anonymous_user_cannot_trade(self):
        response=self.client.post('/api/paper/orders',json=ORDER)
        self.assertEqual(response.status_code,401)
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_closed_or_stale_source_never_writes(self):
        from fastapi import FastAPI
        for source in [snapshot(False),snapshot(seconds=121),snapshot(seconds=-10)]:
            a=FastAPI();calls=[]
            def db(method,table,**kwargs): calls.append((method,table,kwargs));return []
            paper.install(a,db,lambda:source,api.FeedUnavailable)
            with patch.object(paper,'auth_request',return_value={'id':USER}):
                self.assertEqual(TestClient(a).post('/api/paper/orders',json=ORDER,headers=AUTH).status_code,409)
            self.assertTrue(all(x[0]=='GET' for x in calls))

    def test_server_quote_and_authenticated_owner_used(self):
        from fastapi import FastAPI
        a=FastAPI();calls=[]
        def db(method,table,**kwargs):
            calls.append((method,table,kwargs));return [] if method=='GET' else [{'id':1}]
        paper.install(a,db,lambda:snapshot(),api.FeedUnavailable)
        with patch.object(paper,'auth_request',return_value={'id':USER}):
            r=TestClient(a).post('/api/paper/orders',json={**ORDER,'price':1,'user_id':'attacker'},headers=AUTH)
        self.assertEqual(r.status_code,200)
        body=calls[-1][2]['body']
        self.assertEqual(body['p_price'],250)
        self.assertEqual(body['p_user'],USER)
        self.assertIn('eq.'+USER,calls[0][2]['params'].values())

    def test_retry_replays_without_new_quote_or_write(self):
        from fastapi import FastAPI
        a=FastAPI();calls=[]
        def db(method,table,**kwargs):calls.append(method);return [{**ORDER,'id':1}]
        def feed():raise AssertionError('Must not fetch quote for already executed order')
        paper.install(a,db,feed,api.FeedUnavailable)
        with patch.object(paper,'auth_request',return_value={'id':USER}):
            r=TestClient(a).post('/api/paper/orders',json=ORDER,headers=AUTH)
        self.assertTrue(r.json()['replayed']);self.assertEqual(calls,['GET'])

    def test_fractional_or_negative_quantity_rejected(self):
        for qty in [-1,0,1.5,True]:
            self.assertEqual(self.client.post('/api/paper/orders',json={**ORDER,'quantity':qty},headers=AUTH).status_code,422)

    def test_missing_valuation_not_fabricated(self):
        from fastapi import FastAPI
        a=FastAPI();calls=[]
        def db(method,table,**kwargs):
            calls.append(kwargs)
            if method=='POST':return []
            if table.endswith('accounts'):return [{'cash':990000,'initial_cash':1000000}]
            if table.endswith('positions'):return [{'symbol':'MISSING','quantity':10,'cost_basis':10000}]
            return []
        paper.install(a,db,lambda:snapshot(),api.FeedUnavailable)
        with patch.object(paper,'auth_request',return_value={'id':USER}):
            data=TestClient(a).get('/api/paper/portfolio',headers=AUTH).json()
        self.assertIsNone(data['equity']);self.assertIsNone(data['total_pnl'])
        self.assertIsNone(data['positions'][0]['market_value'])
