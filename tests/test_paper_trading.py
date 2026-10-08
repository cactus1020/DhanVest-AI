import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
from frontend.api import index as api
from frontend import paper_trading as paper

USER='11111111-1111-4111-8111-111111111111'
REQUEST='22222222-2222-4222-8222-222222222222'
ORDER={'symbol':'GP','side':'buy','quantity':5,'request_id':REQUEST}
AUTH={'Authorization':'Bearer verified-user-token'}

def snapshot(open=True, seconds=0):
    day=datetime.now(timezone.utc).astimezone(ZoneInfo('Asia/Dhaka')).date().isoformat()
    return {'session':{'isOpen':open,'sessionDate':day},
        'retrieved_at':(datetime.now(timezone.utc)-timedelta(seconds=seconds)).isoformat(),
        'quotes':[{'symbol':'GP','traded':True,'price':250,'session_date':day}]}


class PaperTradingTests(unittest.TestCase):
    def setUp(self): self.client=TestClient(api.app)

    def test_anonymous_user_cannot_trade(self):
        response=self.client.post('/api/paper/orders',json=ORDER)
        self.assertEqual(response.status_code,401)
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_validation_never_echoes_password(self):
        password='secret'
        response=self.client.post('/api/account/signup',json={'email':'bad','password':password})
        self.assertEqual(response.status_code,422)
        self.assertNotIn(password,response.text)

    def test_cross_origin_auth_is_rejected(self):
        with patch.object(paper,'auth_request') as auth:
            response=self.client.post('/api/account/login',json={'email':'test@example.com','password':'secure-password'},headers={'Origin':'https://untrusted.example'})
        self.assertEqual(response.status_code,403);auth.assert_not_called()

    def test_signup_uses_production_confirmation_redirect(self):
        with patch.object(paper,'auth_request',return_value={'access_token':None}) as auth:
            response=self.client.post('/api/account/signup',json={'email':'test@example.com','password':'secure-password'})
        self.assertEqual(response.status_code,200)
        path=auth.call_args.args[0]
        self.assertIn('redirect_to=https%3A%2F%2Fdhanvest.covers.bd%2Fv2%2Fpractice',path)
        self.assertNotIn('localhost',path)

    def test_resend_needs_only_email_and_uses_fixed_production_url(self):
        with patch.object(paper,'auth_request',return_value={}) as auth:
            response=self.client.post('/api/account/resend',json={'email':'TEST@example.com','redirect_to':'https://untrusted.example'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(auth.call_args.args[1],{'type':'signup','email':'test@example.com'})
        self.assertIn('https%3A%2F%2Fdhanvest.covers.bd%2Fv2%2Fpractice',auth.call_args.args[0])
        self.assertNotIn('untrusted',auth.call_args.args[0])

    def test_resend_rejects_bad_email_and_cross_origin_without_sending(self):
        with patch.object(paper,'auth_request') as auth:
            self.assertEqual(self.client.post('/api/account/resend',json={'email':'bad'}).status_code,422)
            self.assertEqual(self.client.post('/api/account/resend',json={'email':'test@example.com'},headers={'Origin':'https://untrusted.example'}).status_code,403)
        auth.assert_not_called()

    def test_invalid_quote_timestamp_never_writes(self):
        from fastapi import FastAPI
        for stamp in ['invalid', '2026-10-07T10:00:00']:
            source=snapshot();source['retrieved_at']=stamp;calls=[];a=FastAPI()
            def db(method,table,**kwargs):calls.append(method);return []
            paper.install(a,db,lambda:source,api.FeedUnavailable)
            with patch.object(paper,'auth_request',return_value={'id':USER}):
                response=TestClient(a).post('/api/paper/orders',json=ORDER,headers=AUTH)
            self.assertEqual(response.status_code,503);self.assertEqual(calls,['GET'])

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
