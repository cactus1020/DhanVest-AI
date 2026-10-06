import unittest
from frontend.news_pipeline import normalize_rows, capture_symbols
from fastapi.testclient import TestClient
from frontend.api.index import app

class ProspectiveNewsTests(unittest.TestCase):
    def test_first_seen_not_backdated_and_revisions_distinct(self):
        item={'id':1,'code':'GP','summary':'Dividend approved','body':'profit increase','filedAt':'2024-01-01'}
        observed='2026-10-07T00:00:00+00:00'
        one=normalize_rows({'rows':[item]},'GP',observed)[0]
        two=normalize_rows({'rows':[{**item,'body':'profit decrease'}]},'GP',observed)[0]
        self.assertEqual(one['available_at'],observed)
        self.assertNotEqual(one['event_id'],two['event_id'])
        self.assertNotIn('body',one)
        self.assertEqual(one['availability_basis'],'prospective_capture')

    def test_incomplete_response_rejected(self):
        with self.assertRaises(ValueError):normalize_rows({'rows':[],'truncated':True},'GP','2026-10-07T00:00:00+00:00')

    def test_partial_source_failure_does_not_discard_other_company(self):
        def fetch(path,params,ttl):
            if params['code']=='BAD':raise ValueError()
            return {'rows':[{'id':1,'code':'GP','summary':'Announcement','filedAt':'2024-01-01'}]}
        events,done,failed=capture_symbols(['GP','BAD'],fetch)
        self.assertEqual(done,1);self.assertEqual(failed,['BAD']);self.assertEqual(len(events),1)

    def test_job_not_publicly_triggerable(self):
        self.assertEqual(TestClient(app).get('/api/jobs/news-sync').status_code,401)
