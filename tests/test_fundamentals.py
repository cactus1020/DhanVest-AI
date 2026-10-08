import json, unittest
from datetime import date
from frontend.fundamentals import company_payload, fiscal_end, attach_fundamentals
from frontend.research import score_universe
from scripts.import_fundamentals import validate
from scripts.collect_newspaper_archive import matches,parse_archive

class FundamentalsTests(unittest.TestCase):
    def test_refresh_is_protected_and_missing_company_does_not_erase_others(self):
        from fastapi.testclient import TestClient
        from frontend.api.index import app
        from frontend.fundamental_jobs import capture
        self.assertEqual(TestClient(app).get('/api/jobs/fundamentals-sync').status_code,401)
        def fetch(symbol):
            if symbol in ['BAD','BSCPLC']:raise ValueError('Unavailable')
            return {'code':symbol,'name':'Company','sector':'Bank','yearEnd':'December','multiYearFinancials':[{'year':2025,'epsBasic':10,'nav':50,'profit':100}]}
        records,count,failed=capture([{'id':1,'symbol':'GOOD'},{'id':2,'symbol':'BAD'}],fetch)
        self.assertEqual(count,1);self.assertEqual(len(records),1);self.assertIn('BAD',failed)
        self.assertEqual(records[0]['debt_to_equity'],None)

    def test_exact_company_payload_and_real_fiscal_end(self):
        payload={'code':'GP','multiYearFinancials':[]}
        html='<script>self.__next_f.push('+json.dumps([1,'1:{"company":'+json.dumps(payload,separators=(',',':'))+'}'])+')</script>'
        self.assertEqual(company_payload(html,'GP')['code'],'GP')
        with self.assertRaises(ValueError):company_payload(html,'ROBI')
        self.assertEqual(fiscal_end(2025,'June'),'2025-06-30')

    def test_missing_debt_never_becomes_zero_and_inputs_not_overwritten(self):
        stocks=[{'id':1,'symbol':'GP','sector':'General'}]
        rows=[{'stock_id':1,'date':'2026-10-06','close_price':240.2,'volume':1,'source_verified':True,'source_url':'https://example.org/prices'}]
        record={'stock_id':1,'period_end':'2025-12-31','period_kind':'annual','eps':21.9,'sector':'Telecom','company_name':'Grameenphone',
                'source_verified':True,'source_observed_at':'2026-10-08T00:00:00+00:00','source_url':'https://www.dse.com.bd/company/GP'}
        companies,enriched,_=attach_fundamentals(stocks,rows,[record],date(2026,10,8))
        result=score_universe(companies,enriched,date(2026,10,8))[0]
        self.assertIsNone(result['quality']);self.assertIsNone(result['fundamentals']['debt_to_equity'] if 'debt_to_equity' in result['fundamentals'] else None)
        self.assertAlmostEqual(result['fundamentals']['pe_ratio'],240.2/21.9)
        self.assertNotIn('pe_ratio',rows[0]);self.assertEqual(stocks[0]['sector'],'General')

    def test_reported_ratios_and_three_sourced_sector_peers_enable_factors(self):
        stocks=[{'id':1,'symbol':'GP','sector':'Telecom'},{'id':2,'symbol':'ROBI','sector':'Telecom'}]
        rows=[{'stock_id':i,'date':'2026-10-06','close_price':100,'volume':1,'source_verified':True,'source_url':'https://www.dse.com.bd/'} for i in [1,2]]
        records=[{'stock_id':i,'period_end':'2025-12-31','period_kind':'annual','eps':10,'roe':20,'debt_to_equity':.5,'roe_method':'reported','debt_method':'reported','company_name':str(i),'sector':'Telecom','source_verified':True,'source_observed_at':'2026-10-08T00:00:00+00:00','source_url':'https://www.dse.com.bd/'} for i in [1,2]]
        companies,enriched,_=attach_fundamentals(stocks,rows,records,date(2026,10,8))
        peer={'symbol':'BSCPLC','sector':'Telecom','period_end':'2025-06-30','period_kind':'annual','eps':10,'benchmark_price':100,'price_date':'2026-10-08','source_verified':True,'source_url':'https://www.dse.com.bd/company/BSCPLC'}
        result=score_universe(companies,enriched,date(2026,10,8),[peer])
        self.assertTrue(all(r['value'] is not None and r['quality'] is not None for r in result))
        peer['source_verified']=False
        self.assertTrue(all(r['value'] is None for r in score_universe(companies,enriched,date(2026,10,8),[peer])))

    def test_import_rejects_unreviewed_debt_ratio_before_write(self):
        row={'record_id':'a','period_end':'2025-12-31','source_observed_at':'2026-10-08T00:00:00+00:00','source_url':'https://www.dse.com.bd/','source_verified':True,'debt_to_equity':.5}
        with self.assertRaises(ValueError):validate([row])

class NewspaperMappingTests(unittest.TestCase):
    profiles=[{'symbol':'GP','name':'Grameenphone Ltd.','sector':'Telecom'},{'symbol':'ROBI','name':'Robi Axiata PLC','sector':'Telecom'},{'symbol':'BRACBANK','name':'BRAC Bank PLC','sector':'Bank'}]
    def test_company_story_stays_specific_and_sector_news_maps_sector(self):
        symbols,_=matches('Grameenphone posts telecom profit drop',self.profiles)
        self.assertEqual(symbols,['GP'])
        symbols,_=matches('Telecom operators face new tax',self.profiles)
        self.assertEqual(symbols,['GP','ROBI'])
        self.assertEqual(matches('GP declares dividend',self.profiles)[0],['GP'])
        import re
        outside=[re.compile(r'\bUttara Bank\b',re.I)]
        self.assertEqual(matches('Uttara Bank profit drops',self.profiles,outside)[0],[])

    def test_dates_verified_and_no_article_body_stored(self):
        html="Search date: 18-07-2025<h2>Grameenphone profit drops</h2><p>FULL BODY MUST NOT BE STORED</p><a href='https://today.thefinancialexpress.com.bd/stock-corporate/gp-story'>Read more</a>"
        events=parse_archive(html,date(2025,7,18),self.profiles,'2026-10-08T00:00:00+00:00')
        self.assertEqual(len(events),1);self.assertNotIn('body',events[0])
        self.assertTrue(events[0]['available_at'].startswith('2025-07-19'))
        with self.assertRaises(ValueError):parse_archive(html,date(2025,7,19),self.profiles,'2026-10-08T00:00:00+00:00')
