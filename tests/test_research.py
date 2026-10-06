import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
import pandas as pd
from fastapi.testclient import TestClient

from frontend.api import index as api
from frontend.research import score_stock, score_universe, verified_history, explain_bangla
from backend.data_validation import load_market_data
from backend.seed_supabase import seed_database
from backend.train_model import features, chronological_folds, train_model

TODAY = date(2026, 10, 6)
STOCK = {"id": 1, "symbol": "TEST", "name": "Test Company", "sector": "Bank"}


def history(count=61, **updates):
    days = pd.date_range(end=TODAY.isoformat(), periods=count, freq=pd.offsets.CustomBusinessDay(weekmask="Sun Mon Tue Wed Thu"))
    return [dict(stock_id=1, date=day.date().isoformat(), close_price=100 + i, volume=100000, source_verified=True, source_url="https://example.org/filing", **updates) for i, day in enumerate(days)]


class ScoringTests(unittest.TestCase):
    def test_missing_fundamentals_are_not_neutral_scores(self):
        result = score_stock(STOCK, history(), today=TODAY)
        self.assertIsNone(result["quality"])
        self.assertIsNone(result["value"])
        self.assertEqual(result["coverage"], 40)
        self.assertAlmostEqual(sum(result["weights"].values()), 1)
        self.assertAlmostEqual(result["composite"], result["momentum"] * .625 + result["liquidity"] * .375, places=2)

    def test_unsourced_legacy_rows_never_produce_scores(self):
        rows = history()
        for row in rows: row["source_verified"] = False
        result = score_stock(STOCK, rows, today=TODAY)
        self.assertIsNone(result["composite"])
        self.assertEqual(result["coverage"], 0)

    def test_scoring_order_is_chronological(self):
        rows = history()
        self.assertEqual(score_stock(STOCK, rows, today=TODAY), score_stock(STOCK, rows[::-1], today=TODAY))

    def test_duplicate_dates_fail_closed(self):
        rows = history()
        with self.assertRaises(ValueError): verified_history(rows + [rows[0]], TODAY)

    def test_future_rows_are_excluded(self):
        row = history(1)[0]
        row["date"] = (TODAY + timedelta(days=1)).isoformat()
        self.assertEqual(verified_history([row], TODAY), [])

    def test_invalid_prices_and_volume_are_excluded(self):
        for field, value in [("close_price", 0), ("close_price", float('nan')), ("volume", -1)]:
            row = history(1)[0]
            row[field] = value
            self.assertEqual(verified_history([row], TODAY), [])

    def test_short_history_is_unavailable(self):
        result = score_stock(STOCK, history(10), today=TODAY)
        self.assertIsNone(result["momentum"])
        self.assertIsNone(result["liquidity"])
        self.assertIsNone(result["composite"])

    def test_stale_market_and_fundamentals_are_disclosed(self):
        rows = history(61, roe=20, debt_to_equity=.5, pe_ratio=10, fundamentals_date="2025-01-01")
        result = score_stock(STOCK, rows, sector_pe=15, today=date(2027, 1, 1))
        self.assertTrue(result["stale"])
        self.assertIsNone(result["quality"])
        self.assertIsNone(result["value"])

    def test_sector_value_needs_three_fresh_peers(self):
        stocks = [dict(STOCK, id=i, symbol=str(i)) for i in [1, 2, 3]]
        rows = []
        for stock, pe in zip(stocks, [10, 20, 30]):
            row = history(1, pe_ratio=pe, fundamentals_date=TODAY.isoformat())[0]
            row["stock_id"] = stock["id"]
            rows.append(row)
        result = score_universe(stocks, rows, TODAY)
        self.assertEqual(next(s for s in result if s["id"] == 1)["value"], 100)
        self.assertTrue(all(s["value"] is None for s in score_universe(stocks[:2], rows, TODAY)))

    def test_explanation_includes_missing_data_and_disclaimer(self):
        text = explain_bangla(score_stock(STOCK, history(), today=TODAY))
        self.assertIn("আংশিক", text)
        self.assertIn("বিনিয়োগের পরামর্শ নয়", text)
        self.assertNotIn("কেনা উচিত", text)


class ApiTests(unittest.TestCase):
    def setUp(self): self.client = TestClient(api.app)

    def test_app_starts_without_external_credentials(self):
        with patch.dict('os.environ', {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}):
            response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'database_not_configured')
        self.assertEqual(self.client.get('/research').status_code, 200)

    def test_legacy_schema_keeps_stock_names_but_does_not_trust_old_scores(self):
        row = {'stock_id': 1, 'date': '2026-10-06', 'close_price': 100, 'volume': 1000}
        with patch.object(api, 'read_all', side_effect=[[STOCK], [row], [], []]):
            response = self.client.get('/api/stocks')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['symbol'], STOCK['symbol'])
        self.assertIsNone(response.json()[0]['composite'])
        self.assertEqual(response.json()[0]['coverage'], 0)

    def test_health_discloses_missing_schema_without_calling_database_down(self):
        missing = api.DatabaseUnavailable('database_schema_missing', 'Setup incomplete.')
        with patch.object(api, 'database_request', side_effect=[[], [], missing, missing]):
            response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'degraded')
        self.assertEqual(response.json()['database'], 'reachable')
        self.assertFalse(response.json()['features']['waitlist'])

    def test_schema_error_is_distinct_from_authentication_failure(self):
        with patch.dict('os.environ', {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "private-secret"}), patch.object(api.httpx, 'Client') as factory:
            factory.return_value.__enter__.return_value.request.return_value = httpx.Response(404, json={'code': 'PGRST205'})
            response = self.client.post('/api/waitlist', json={'email': 'test@example.com'})
        self.assertEqual(response.json()['code'], 'database_schema_missing')

    def test_database_failure_does_not_leak_credentials(self):
        with patch.dict('os.environ', {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "private-secret"}), patch.object(api.httpx, 'Client') as factory:
            factory.return_value.__enter__.return_value.request.side_effect = httpx.ConnectError('private-secret')
            response = self.client.get('/api/stocks')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private-secret', response.text)

    def test_invalid_database_auth_is_sanitized(self):
        with patch.dict('os.environ', {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "private-secret"}), patch.object(api.httpx, 'Client') as factory:
            factory.return_value.__enter__.return_value.request.return_value = httpx.Response(401, json={"message": "private-secret"})
            response = self.client.get('/api/stocks')
        self.assertEqual(response.json()['code'], 'database_credentials_invalid')
        self.assertNotIn('private-secret', response.text)

    def test_waitlist_success_requires_database_write(self):
        with patch.object(api, 'database_request', return_value=[]) as write:
            response = self.client.post('/api/waitlist', json={"email": " Investor@Example.com "})
        self.assertEqual(response.json()['status'], 'saved')
        self.assertEqual(write.call_args.kwargs['body']['email'], 'investor@example.com')
        self.assertEqual(write.call_args.kwargs['params']['on_conflict'], 'email')

    def test_failed_waitlist_write_is_not_reported_as_success(self):
        with patch.object(api, 'database_request', side_effect=api.DatabaseUnavailable('database_unreachable', 'Database unavailable.')):
            response = self.client.post('/api/waitlist', json={"email": "investor@example.com"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('saved', response.text)

    def test_invalid_email_and_bot_field_never_write(self):
        with patch.object(api, 'database_request') as write:
            self.assertEqual(self.client.post('/api/waitlist', json={"email": "invalid"}).status_code, 422)
            self.assertEqual(self.client.post('/api/waitlist', json={"email": "x@example.com", "website": "spam"}).status_code, 400)
        write.assert_not_called()

    def test_cross_origin_waitlist_request_is_rejected(self):
        with patch.object(api, 'database_request') as write:
            response = self.client.post('/api/waitlist', headers={'Origin': 'https://other.example'}, json={"email": "x@example.com"})
        self.assertEqual(response.status_code, 403)
        write.assert_not_called()

    def test_explanation_uses_verified_scores(self):
        result = score_stock(STOCK, history(), today=TODAY)
        with patch.object(api, 'current_stocks', return_value=[result]):
            response = self.client.post('/api/explain', json={"stock_id": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['method'], 'rules')

    def test_pagination_does_not_silently_drop_history(self):
        with patch.object(api, 'database_request', side_effect=[[{'id': n} for n in range(1000)], [{'id': 1000}]]) as read:
            result = api.read_all('daily_data', source_verified='eq.true')
        self.assertEqual(len(result), 1001)
        self.assertEqual(read.call_args.kwargs['params']['offset'], 1000)

    def test_optional_ai_key_stays_in_server_header_and_output_is_cached(self):
        stock = score_stock(STOCK, history(), today=TODAY)
        text = 'উপলব্ধ তথ্য অনুযায়ী কিছু সূচক তুলনামূলক বেশি, তবে কিছু তথ্য অনুপস্থিত। বিস্তারিত যাচাই করুন।'
        result = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}}]}
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'private-ai-key', 'GEMINI_MODEL': 'test-model'}), patch.object(api, 'database_request', side_effect=[[], []]) as database, patch.object(api.httpx, 'Client') as factory:
            factory.return_value.__enter__.return_value.post.return_value = httpx.Response(200, json=result)
            output, method = api.generated_explanation(stock)
        self.assertEqual(method, 'ai')
        call = factory.return_value.__enter__.return_value.post.call_args
        self.assertEqual(call.kwargs['headers']['x-goog-api-key'], 'private-ai-key')
        self.assertNotIn('private-ai-key', call.args[0])
        self.assertNotIn('private-ai-key', output)
        self.assertEqual(database.call_args.args[0], 'POST')
        self.assertIn('signature', database.call_args.kwargs['body'])

    def test_cached_ai_does_not_make_another_paid_request(self):
        stock = score_stock(STOCK, history(), today=TODAY)
        text = 'উপলব্ধ তথ্য আংশিক; এই স্কোর ভবিষ্যতের ফলাফল নির্দেশ করে না। তথ্য ও শিক্ষার জন্য।'
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'private-ai-key', 'GEMINI_MODEL': 'test-model'}), patch.object(api, 'database_request', return_value=[{'explanation_bn': text}]), patch.object(api.httpx, 'Client') as factory:
            output, method = api.generated_explanation(stock)
        self.assertEqual(method, 'ai_cached')
        factory.assert_not_called()

    def test_unsafe_ai_output_falls_back_without_being_saved(self):
        stock = score_stock(STOCK, history(), today=TODAY)
        result = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'এই শেয়ার এখন buy now, আগামীতে নিশ্চিত লাভ হবে এবং দাম বাড়বে।'}]}}]}
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'private-ai-key', 'GEMINI_MODEL': 'test-model'}), patch.object(api, 'database_request', return_value=[]) as database, patch.object(api.httpx, 'Client') as factory:
            factory.return_value.__enter__.return_value.post.return_value = httpx.Response(200, json=result)
            text, method = api.generated_explanation(stock)
        self.assertEqual(method, 'rules')
        self.assertNotIn('buy now', text)
        self.assertEqual(database.call_count, 1)

    def test_invented_figures_are_rejected(self):
        stock = score_stock(STOCK, history(), today=TODAY)
        self.assertFalse(api.valid_explanation('এই প্রতিষ্ঠানের স্কোর 999.0 এবং এটি অত্যন্ত ভালো বিনিয়োগ।', stock))

    def test_ai_cache_is_invalidated_when_underlying_scores_change(self):
        stock = score_stock(STOCK, history(), today=TODAY)
        text = 'উপলব্ধ তথ্য আংশিক; এই স্কোর ভবিষ্যতের ফলাফল নির্দেশ করে না। তথ্য ও শিক্ষার জন্য।'
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'private-ai-key', 'GEMINI_MODEL': 'test-model'}), patch.object(api, 'database_request', return_value=[{'explanation_bn': text}]) as database:
            api.generated_explanation(stock)
            old_signature = database.call_args.kwargs['params']['signature']
            api.generated_explanation(dict(stock, liquidity=10.0))
            new_signature = database.call_args.kwargs['params']['signature']
        self.assertNotEqual(old_signature, new_signature)


class DataAndModelTests(unittest.TestCase):
    def test_bundled_undated_csv_is_rejected_before_any_write(self):
        path = Path(__file__).resolve().parents[1] / 'real_dse_data.csv'
        with patch('backend.seed_supabase.database_request') as write, self.assertRaisesRegex(ValueError, 'date'):
            seed_database(path, 'https://example.org/archive', True)
        write.assert_not_called()

    def test_bad_dates_and_duplicate_rows_are_rejected(self):
        for data in [
            'symbol,date,close,volume\nX,2026-10-02,100,10\n',
            'symbol,date,close,volume\nX,2026-10-06,100,10\nX,2026-10-06,110,10\n',
            'symbol,date,close,volume\nX,2026-10-06,-1,10\n',
        ]:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'data.csv'
                path.write_text(data)
                with self.assertRaises(ValueError): load_market_data(path)

    def test_import_preserves_source_dates_and_never_deletes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.csv'
            path.write_text('symbol,date,close,volume\nX,2026-10-06,100,10\n')
            with patch('backend.seed_supabase.database_request', side_effect=[[{'id': 1}], []]) as db:
                seed_database(path, 'https://example.org/archive', True)
        self.assertEqual(db.call_args.kwargs['body'][0]['date'], '2026-10-06')
        self.assertTrue(db.call_args.kwargs['body'][0]['source_verified'])
        self.assertNotIn('DELETE', [call.args[0] for call in db.call_args_list])

    def test_model_folds_purge_overlapping_future_labels(self):
        dates = pd.date_range('2025-01-01', periods=250, freq=pd.offsets.CustomBusinessDay(weekmask='Sun Mon Tue Wed Thu'))
        frame = pd.DataFrame({'symbol': 'X', 'date': dates, 'close': [100 + (i % 11) for i in range(250)], 'volume': 100})
        frame = features(frame)
        self.assertEqual(len(frame), 250 - 19 - 5)
        folds = list(chronological_folds(frame))
        self.assertEqual(len(folds), 3)
        for train, test in folds:
            self.assertLess(train['label_date'].max(), test['date'].min())
            self.assertTrue(set(train.index).isdisjoint(test.index))

    def test_synthetic_walk_forward_reports_baseline_and_three_folds(self):
        dates = pd.date_range('2025-01-01', periods=250, freq=pd.offsets.CustomBusinessDay(weekmask='Sun Mon Tue Wed Thu'))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'synthetic.csv'
            pd.DataFrame({'symbol': 'X', 'date': dates.strftime('%Y-%m-%d'), 'close': [100 + (i % 11) for i in range(250)], 'volume': 100}).to_csv(path, index=False)
            report = train_model(path, 'https://example.org/test-fixture', True, Path(temp) / 'report.json')
            self.assertEqual(len(report['folds']), 3)
            self.assertTrue(all('majority_baseline_accuracy' in fold for fold in report['folds']))
            self.assertEqual(report['status'], 'research_only')


if __name__ == '__main__': unittest.main()
