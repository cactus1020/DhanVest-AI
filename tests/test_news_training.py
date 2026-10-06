import unittest
import pandas as pd
from backend.train_news_model import attach_news
from frontend import market_data as feed
from unittest.mock import patch

class NewsTrainingTests(unittest.TestCase):
    def test_news_join_uses_prediction_cutoff_and_company(self):
        frame=pd.DataFrame({'symbol':['GP']*5,'date':pd.to_datetime(['2026-01-04','2026-01-05','2026-01-06','2026-01-07','2026-01-08']),'close':[100,102,101,103,104]})
        events=[{'event_id':'1','symbols':['GP'],'title':'Dividend announcement','available_at':'2026-01-05T15:00:00+06:00'}, {'event_id':'2','symbols':['OTHER'],'title':'Other company','available_at':'2026-01-04T10:00:00+06:00'}]
        result=attach_news(frame,events,2)
        self.assertEqual(result['news_count'].tolist(),[0,0,1])
        self.assertEqual(result['target'].tolist(),[1,1,1])
        self.assertNotIn('Other company',result.iloc[-1]['news_text'])

    def test_duplicate_story_counts_once(self):
        frame=pd.DataFrame({'symbol':['GP']*3,'date':pd.to_datetime(['2026-01-04','2026-01-05','2026-01-06']),'close':[100,101,102]})
        event={'event_id':'1','symbols':['GP'],'title':'Dividend','available_at':'2026-01-04T09:00:00+06:00'}
        result=attach_news(frame,[event,event],2)
        self.assertEqual(result.iloc[0]['news_count'],1)

    def test_clamped_archive_dates_are_excluded_not_relabelled(self):
        row={'date':'2024-10-06','tradingCode':'GP','closep':100,'volume':20}
        with patch.object(feed,'fetch_json',return_value={'rows':[row],'total':1}):
            result=feed.company_history('GP','2021-01-01','2021-12-31')
        self.assertEqual(result['points'],[])
        self.assertEqual(result['excluded_out_of_range'],1)
