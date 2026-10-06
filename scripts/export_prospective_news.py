"""Export private first-seen announcement data for point-in-time training."""
import argparse
import json
from pathlib import Path
from frontend.api.index import read_all

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    events=read_all('dhanvest_news_events',order='available_at.asc')
    target=Path(args.output)
    if 'data' not in target.parts:
        parser.error('Write private research exports inside the ignored data directory.')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as output:
        for event in events:output.write(json.dumps(event,ensure_ascii=False)+'\n')
    print(f'Exported {len(events)} prospective versions. No files overwritten; no production model changed.')

if __name__=='__main__':main()
