import unittest
from scripts.resolve_shadow_predictions import outcome

class ShadowOutcomeTests(unittest.TestCase):
    def test_sessions_not_calendar_days_and_flat_is_separate(self):
        prediction={'id':'test','base_date':'2026-10-01','base_price':100,'horizon_sessions':2}
        rows=[{'date':d,'close_price':p,'source_verified':True,'source_url':'https://www.dsebd.org/'} for d,p in [('2026-10-04',105),('2026-10-05',100)]]
        self.assertIsNone(outcome(prediction,rows[:1]))
        result=outcome(prediction,rows);self.assertEqual(result['outcome_date'],'2026-10-05');self.assertEqual(result['actual_direction'],'flat')
    def test_unverified_and_duplicate_sessions_not_counted(self):
        prediction={'id':'test','base_date':'2026-10-01','base_price':100,'horizon_sessions':2}
        row={'date':'2026-10-04','close_price':105,'source_verified':True,'source_url':'https://www.dsebd.org/'}
        self.assertIsNone(outcome(prediction,[row,{**row,'source_verified':False}]))
        with self.assertRaises(ValueError):outcome(prediction,[row,row])
