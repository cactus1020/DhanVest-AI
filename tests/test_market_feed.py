import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from frontend import market_data as feed
from frontend.api import index as api

SESSION={'sessionDate':'2026-10-06','isOpen':False}
PAYLOAD={'session':SESSION,'cols':['code','board','assetType','ltp','ycp','volume','close'], 'rows':[['GP','PUBLIC','EQ',110,100,20,110],['NO','PUBLIC','EQ',0,100,0,100],['FUND','PUBLIC','MF',10,10,1,10]]}

class MarketFeedTests(unittest.TestCase):
    def test_quotes_separate_no_trade_and_exclude_funds(self):
        quotes,_=feed.parse_prices(PAYLOAD)
        self.assertEqual(len(quotes),2)
        self.assertEqual(quotes[0]['change_percent'],10)
        self.assertIsNone(quotes[1]['price'])
        self.assertIsNone(quotes[1]['change_percent'])

    def test_invalid_or_duplicate_feed_fails_closed(self):
        for payload in [dict(PAYLOAD,rows=PAYLOAD['rows']+[PAYLOAD['rows'][0]]), dict(PAYLOAD,session={'sessionDate':'2099-01-01'}),dict(PAYLOAD,cols=['code'])]:
            with self.assertRaises(feed.FeedUnavailable):feed.parse_prices(payload)

    def test_archive_does_not_silently_accept_truncation(self):
        with patch.object(feed,'fetch_json',return_value={'rows':[],'total':500}):
            with self.assertRaises(feed.FeedUnavailable):feed.company_history('GP','2026-01-01','2026-10-06')

    def test_news_titles_are_attributed_without_republishing_bodies(self):
        row={'id':'1','code':'GP','summary':'Dividend','body':'PRIVATE FULL BODY','filedAt':'2026-01-01'}
        with patch.object(feed,'fetch_json',return_value={'rows':[row,row]}):result=feed.company_news('GP')
        self.assertEqual(len(result['items']),1)
        self.assertNotIn('body',result['items'][0])

    def test_public_api_validates_symbol_and_job_requires_secret(self):
        client=TestClient(api.app)
        self.assertEqual(client.get('/api/market/GP%20BAD/news').status_code,422)
        with patch.object(api,'market_snapshot') as snapshot:
            self.assertEqual(client.get('/api/jobs/market-sync').status_code,401)
            snapshot.assert_not_called()

    def test_job_batches_records_and_preserves_history(self):
        snapshot={'session':SESSION,'quotes':feed.parse_prices(PAYLOAD)[0],'source_url':'https://www.dsebd.org/api/live/prices','retrieved_at':'2026-10-06T12:00:00Z'}
        with patch.dict('os.environ',{'CRON_SECRET':'test-secret'}),patch.object(api,'market_snapshot',return_value=snapshot),patch.object(api,'read_all',return_value=[{'id':1,'symbol':'GP'}]),patch.object(api,'database_request',side_effect=[[{'id':2}],[],[]]) as db:
            response=TestClient(api.app).get('/api/jobs/market-sync',headers={'Authorization':'Bearer test-secret'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['records_processed'],1)
        self.assertEqual(db.call_args_list[1].args,('POST','market_history'))
        self.assertEqual(db.call_args_list[1].kwargs['prefer'],'resolution=ignore-duplicates,return=minimal')
        self.assertFalse(any(call.args[0]=='DELETE' for call in db.call_args_list))
