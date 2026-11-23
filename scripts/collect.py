"""Discover metadata in DBLP. Results stay pending until research-track review.

Usage: python3 scripts/collect.py [--venue ICSE] [--year 2025]
Successful individual queries are retained when another source fails.
"""
import argparse
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from common import read, write, now, identity

def fetch(url):
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'SE-Figure-Atlas/0.1 (research bibliography)'})
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))

def matches(info, venue, stream):
    # Shared PACM streams need issue-level filtering to avoid cross-venue mixing.
    if stream in ('journals/pacmse', 'journals/pacmpl'):
        issue = str(info.get('number', '')).upper()
        return issue.startswith(venue.get('issue', '__none__'))
    actual = info.get('venue', '')
    actual = ' '.join(actual) if isinstance(actual, list) else actual
    if venue['type'] == 'conference':
        return actual.upper().strip() == venue['id']
    return True

def normalize(info, venue):
    authors = info.get('authors', {}).get('author', [])
    if not isinstance(authors, list):
        authors = [authors]
    authors = [a.get('text', '') if isinstance(a, dict) else a for a in authors]
    paper = {
        'id': 'dblp:' + info['key'], 'dblp_key': info['key'],
        'title': info['title'], 'authors': authors,
        'venue': venue['id'], 'year': int(info['year']),
        'doi': info.get('doi', ''),
        'source_url': 'https://dblp.org/rec/' + info['key'],
        'verification': 'pending', 'figure_status': 'pending',
        'tags': [], 'added_at': now()[:10]
    }
    paper['id'] = identity(paper)
    return paper

def merge(existing, new):
    by_id = {identity(p): p for p in existing}
    by_key = {p['dblp_key']: p for p in existing if p.get('dblp_key')}
    for paper in new:
        key = identity(paper)
        previous = by_id.get(key) or by_key.get(paper.get('dblp_key'))
        if previous is None:
            by_id[key] = paper
            if paper.get('dblp_key'):
                by_key[paper['dblp_key']] = paper
        else:
            # Preserve all manually curated metadata and review decisions.
            previous.setdefault('dblp_key', paper.get('dblp_key'))
            if not previous.get('doi') and paper.get('doi'):
                previous['doi'] = paper['doi']
    return sorted(by_id.values(), key=lambda p: (-p['year'], p['venue'], p['title']))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--venue')
    parser.add_argument('--year', type=int, choices=[2025, 2026])
    args = parser.parse_args()
    scope = read('scope.json')
    if args.venue and args.venue not in [v['id'] for v in scope['venues']]:
        parser.error('unknown venue')
    papers = read('papers.json', [])
    status = read('status.json', {})
    status.update(last_attempt=now(), errors=[], queries=[])
    for venue in scope['venues']:
        if args.venue and venue['id'] != args.venue:
            continue
        for year in ([args.year] if args.year else scope['years']):
            for stream in venue['streams']:
                offset = 0
                label = f'{venue["id"]}/{year}/{stream}'
                try:
                    while True:
                        params = urlencode({'q': f'stream:{stream}: year:{year}:', 'format': 'json', 'h': 100, 'f': offset})
                        result = fetch('https://dblp.org/search/publ/api?' + params)['result']['hits']
                        hits = result.get('hit', [])
                        if isinstance(hits, dict):
                            hits = [hits]
                        records = [normalize(h['info'], venue) for h in hits
                                   if int(h['info'].get('year', 0)) == year
                                   and matches(h['info'], venue, stream)
                                   and h['info'].get('type') in ('Journal Articles', 'Conference and Workshop Papers')]
                        papers = merge(papers, records)
                        write('papers.json', papers)
                        offset += len(hits)
                        if offset >= int(result.get('@total', 0)) or not hits:
                            break
                        time.sleep(2)
                    status['queries'].append({'query': label, 'status': 'ok', 'hits': offset})
                except Exception as exc:
                    status['errors'].append({'query': label, 'error': type(exc).__name__ + ': ' + str(exc)[:250]})
                finally:
                    write('status.json', status)
                time.sleep(2)
    if not status['errors']:
        status['last_success'] = now()
    status['note'] = '自动发现结果待正式研究论文资格核验；图片另行提取和审核。'
    write('status.json', status)
    print(json.dumps({'papers': len(papers), 'failed_queries': len(status['errors'])}))

if __name__ == '__main__':
    from collect_sources import main as collect_sources
    collect_sources()
