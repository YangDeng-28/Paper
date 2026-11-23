"""Shared catalog functions; no third-party dependency required."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import database

ROOT = Path(__file__).resolve().parents[1]

def read(name, default=None):
    if name in database.NAMES:
        return database.read(ROOT,name,default)
    path = ROOT / 'data' / name
    return json.loads(path.read_text('utf-8')) if path.exists() else default

def write(name, value):
    if name in database.NAMES:
        return database.write(ROOT,name,value)
    path = ROOT / 'data' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    temp.replace(path)

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def identity(paper):
    doi = paper.get('doi', '').lower().strip()
    doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi)
    return 'doi:' + doi if doi else paper['id']

def https(url):
    parsed = urlparse(url)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username

def validate(papers, figures, scope):
    allowed = {v['id'] for v in scope['venues']}
    by_id = {p['id']:p for p in papers}
    ids = set()
    for paper in papers:
        assert paper['id'] not in ids, 'duplicate paper id: ' + paper['id']
        ids.add(paper['id'])
        assert paper['venue'] in allowed, 'unknown venue'
        assert paper['year'] in scope['years'], 'out-of-scope year'
        assert paper['title'] and https(paper['source_url']), 'missing title/source'
    figure_ids = set()
    for figure in figures:
        assert figure['id'] not in figure_ids, 'duplicate figure'
        figure_ids.add(figure['id'])
        assert figure['paper_id'] in ids, 'orphan figure'
        assert figure['kind'] in ['framework', 'experiment'], 'unknown figure kind'
        if figure.get('status') == 'published':
            paper = by_id[figure['paper_id']]
            assert paper.get('verification') == 'research_track_verified', 'paper publication eligibility needs verification'
            for field in ['caption', 'number', 'version', 'attribution', 'license']:
                assert figure.get(field), 'missing figure field: ' + field
            assert figure.get('publication_verified') is True, 'publication must have verified provenance and image source'
            assert figure.get('license') != 'unverified', 'unverified reuse basis'
            if figure.get('reviewed'):
                assert figure.get('note'), 'curated figures require a reference note'
            assert https(figure['source_url']) and https(figure['rights_url']), 'missing provenance'
            for field in ['image', 'thumbnail']:
                image = figure.get(field)
                if image is not None:
                    assert https(image) or (re.fullmatch(r'assets/[A-Za-z0-9_./-]+', image) and '..' not in image.split('/')), 'unsafe image'
