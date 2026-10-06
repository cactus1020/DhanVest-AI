"""Validate licensed news exports and build point-in-time event-count features.

No network, database writes, sentiment guesses, or prediction claims.
Input: JSONL with id, title, url, published_at, first_seen_at, kind, symbols.
Kinds: official, report, unverified. Symbols must be explicitly mapped upstream.
"""
import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

KINDS = ('official', 'report', 'unverified')

def timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('News timestamps must be ISO 8601 with a timezone.') from None
    if result.tzinfo is None:
        raise ValueError('News timestamps require a timezone.')
    return result.astimezone(timezone.utc)

def normalize_event(row, known_symbols, now=None):
    now = now or datetime.now(timezone.utc)
    if row.get('kind') not in KINDS:
        raise ValueError('News kind must be official, report, or unverified.')
    title = row.get('title')
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 1000:
        raise ValueError('News title is missing or too long.')
    url = urlsplit(str(row.get('url', '')))
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('News requires an HTTPS source without credentials.')
    published = timestamp(row.get('published_at'))
    seen = timestamp(row.get('first_seen_at'))
    if seen < published or published > now or seen > now:
        raise ValueError('Invalid publication or first-seen chronology.')
    symbols = row.get('symbols')
    if not isinstance(symbols, list) or not symbols or any(not isinstance(s, str) or s not in known_symbols for s in symbols):
        raise ValueError('News symbols require explicit mapping to known stocks.')
    canonical = urlunsplit((url.scheme, url.netloc.lower(), url.path, url.query, ''))
    return {'event_id': hashlib.sha256(canonical.encode()).hexdigest(), 'title':title.strip(), 'url':canonical,
            'published_at':published.isoformat(), 'first_seen_at':seen.isoformat(), 'available_at':seen.isoformat(),
            'kind':row['kind'], 'symbols':sorted(set(symbols))}

def load_events(path, known_symbols, now=None):
    events = {}
    for line_number, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('Each line must be a JSON object.')
            event = normalize_event(row, known_symbols, now)
            prior = events.get(event['event_id'])
            if prior and prior != event:
                raise ValueError('Conflicting copies of a source article require review.')
            events[event['event_id']] = event
        except (ValueError, TypeError, AttributeError) as error:
            raise ValueError(f'News line {line_number}: {error}') from None
    return sorted(events.values(), key=lambda event: event['available_at'])

def event_features(events, symbol, as_of, lookback_days=7):
    cutoff = timestamp(as_of)
    start = cutoff - timedelta(days=lookback_days)
    counts = {f'news_{kind}_count': 0 for kind in KINDS}
    seen = set()
    for event in events:
        if event['event_id'] in seen or symbol not in event['symbols']:
            continue
        available = timestamp(event['available_at'])
        # Only news observed before this exact prediction cutoff is eligible.
        if start < available <= cutoff:
            counts[f"news_{event['kind']}_count"] += 1
            seen.add(event['event_id'])
    return counts

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('--symbols', required=True, help='Comma-separated known stock symbols')
    parser.add_argument('--output', required=True)
    parser.add_argument('--confirm-rights', action='store_true', help='Confirm permission to store and use this export')
    args = parser.parse_args()
    if not args.confirm_rights:
        parser.error('Confirm data-use rights before importing the export.')
    events = load_events(args.input, set(args.symbols.split(',')))
    # Exclusive creation preserves existing exports. Validate everything first.
    with Path(args.output).open('x', encoding='utf-8') as target:
        for event in events:
            target.write(json.dumps(event, ensure_ascii=False) + '\n')
    print(f'Validated {len(events)} source articles. Existing files and databases were untouched.')

if __name__ == '__main__':
    main()
