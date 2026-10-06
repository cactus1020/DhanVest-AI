import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from backend.news_events import normalize_event, load_events, event_features

NOW = datetime(2026,10,6,tzinfo=timezone.utc)
ROW = {'title':'Company announcement','url':'https://example.org/article','kind':'official','symbols':['TEST'],'published_at':'2026-01-01T10:00:00Z','first_seen_at':'2026-01-02T10:00:00Z'}

class NewsEventTests(unittest.TestCase):
    def test_later_observation_cannot_leak_into_earlier_prediction(self):
        event = normalize_event(ROW, {'TEST'}, NOW)
        self.assertEqual(event_features([event], 'TEST', '2026-01-01T12:00:00Z')['news_official_count'],0)
        self.assertEqual(event_features([event,event], 'TEST', '2026-01-02T12:00:00Z')['news_official_count'],1)
        self.assertEqual(event_features([event], 'OTHER', '2026-01-02T12:00:00Z')['news_official_count'],0)

    def test_reject_bad_chronology_entities_and_sources(self):
        for updates in [{'first_seen_at':'2025-01-01T10:00:00Z'}, {'published_at':'2099-01-01T10:00:00Z'}, {'first_seen_at':'2026-01-02T10:00:00'}, {'symbols':['UNKNOWN']}, {'url':'http://example.org/article'}, {'kind':'confirmed_rumor'}]:
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                normalize_event(dict(ROW, **updates), {'TEST'}, NOW)

    def test_exact_duplicates_removed_but_conflicting_articles_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'news.jsonl'
            path.write_text('\n'.join(json.dumps(ROW) for _ in range(2)),encoding='utf-8')
            self.assertEqual(len(load_events(path, {'TEST'}, NOW)),1)
            path.write_text(json.dumps(ROW)+'\n'+json.dumps(dict(ROW,kind='unverified')),encoding='utf-8')
            with self.assertRaises(ValueError): load_events(path, {'TEST'}, NOW)
