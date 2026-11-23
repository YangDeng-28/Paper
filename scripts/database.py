"""SQLite is the canonical store. JSON files are accepted only for first migration."""
import json
import sqlite3
from pathlib import Path

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS papers (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, venue TEXT NOT NULL, year INTEGER NOT NULL,
 doi TEXT, dblp_key TEXT, verification TEXT NOT NULL, metadata TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS papers_venue_year ON papers(venue,year);
CREATE INDEX IF NOT EXISTS papers_title ON papers(title COLLATE NOCASE);
CREATE UNIQUE INDEX IF NOT EXISTS papers_doi ON papers(doi) WHERE doi IS NOT NULL AND doi != '';
CREATE UNIQUE INDEX IF NOT EXISTS papers_dblp ON papers(dblp_key) WHERE dblp_key IS NOT NULL AND dblp_key != '';
CREATE TABLE IF NOT EXISTS figures (
 id TEXT PRIMARY KEY, paper_id TEXT NOT NULL REFERENCES papers(id), kind TEXT NOT NULL,
 status TEXT NOT NULL, reviewed INTEGER NOT NULL, metadata TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS figures_paper ON figures(paper_id);
CREATE INDEX IF NOT EXISTS figures_status_kind ON figures(status,kind);
CREATE TABLE IF NOT EXISTS state (name TEXT PRIMARY KEY, payload TEXT NOT NULL);
PRAGMA user_version=1;
'''
NAMES = {'papers.json':'papers','figures.json':'figures','status.json':'state','harvest.json':'state'}

def connect(root):
    path = Path(root)/'data/catalog.sqlite3'
    path.parent.mkdir(parents=True,exist_ok=True)
    conn = sqlite3.connect(path,timeout=30)
    conn.executescript(SCHEMA)
    return conn

def save(conn,name,value):
    table = NAMES[name]
    if table == 'state':
        conn.execute('INSERT INTO state(name,payload) VALUES (?,?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload',(name,json.dumps(value,ensure_ascii=False)))
        return
    conn.execute('CREATE TEMP TABLE IF NOT EXISTS incoming_ids (id TEXT PRIMARY KEY)')
    conn.execute('DELETE FROM incoming_ids')
    conn.executemany('INSERT INTO incoming_ids VALUES (?)',[(v['id'],) for v in value])
    if table == 'papers':
        rows=[(v['id'],v['title'],v['venue'],v['year'],v.get('doi','').strip().lower(),v.get('dblp_key'),v.get('verification','pending'),json.dumps(v,ensure_ascii=False)) for v in value]
        conn.executemany('''INSERT INTO papers VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,venue=excluded.venue,year=excluded.year,doi=excluded.doi,
          dblp_key=excluded.dblp_key,verification=excluded.verification,metadata=excluded.metadata''',rows)
    else:
        rows=[(v['id'],v['paper_id'],v['kind'],v['status'],bool(v.get('reviewed')),json.dumps(v,ensure_ascii=False)) for v in value]
        conn.executemany('''INSERT INTO figures VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
          paper_id=excluded.paper_id,kind=excluded.kind,status=excluded.status,reviewed=excluded.reviewed,metadata=excluded.metadata''',rows)
    conn.execute(f'DELETE FROM {table} WHERE id NOT IN (SELECT id FROM incoming_ids)')

def migrate(root):
    path=Path(root)/'data/catalog.sqlite3'
    if path.exists():
        return
    conn=connect(root)
    try:
        with conn:
            for name in NAMES:
                file=Path(root)/'data'/name
                if file.exists(): save(conn,name,json.loads(file.read_text('utf-8')))
    except Exception:
        conn.close(); path.unlink(missing_ok=True); raise
    finally:
        conn.close()

def read(root,name,default=None):
    migrate(root)
    conn=connect(root)
    try:
        if NAMES[name]=='state':
            row=conn.execute('SELECT payload FROM state WHERE name=?',(name,)).fetchone()
            return json.loads(row[0]) if row else default
        order='year DESC,venue,title' if NAMES[name]=='papers' else 'id'
        return [json.loads(row[0]) for row in conn.execute(f'SELECT metadata FROM {NAMES[name]} ORDER BY {order}')]
    finally: conn.close()

def write(root,name,value):
    migrate(root)
    conn=connect(root)
    try:
        with conn: save(conn,name,value)
    finally: conn.close()

def stats(root):
    conn=connect(root)
    try:
        return {'papers':conn.execute('SELECT count(*) FROM papers').fetchone()[0],
                'figures':conn.execute('SELECT count(*) FROM figures').fetchone()[0],
                'integrity':conn.execute('PRAGMA integrity_check').fetchone()[0],
                'foreign_key_errors':conn.execute('PRAGMA foreign_key_check').fetchall()}
    finally: conn.close()

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    migrate(root)
    print(json.dumps(stats(root),ensure_ascii=False))
