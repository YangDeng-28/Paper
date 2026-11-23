import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import database
import build

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'data').mkdir()
        self.paper={'id':'p1','title':'Example','authors':[],'venue':'ICSE','year':2025,'doi':'10.1/example','verification':'research_track_verified','source_url':'https://example.org/p1'}
        (self.root/'data/papers.json').write_text(json.dumps([self.paper]))
        (self.root/'data/figures.json').write_text('[]')
        database.migrate(self.root)

    def tearDown(self):self.tmp.cleanup()

    def test_migration_is_idempotent_and_ignores_stale_json(self):
        p={**self.paper,'title':'Updated in database'}
        database.write(self.root,'papers.json',[p]);database.migrate(self.root)
        self.assertEqual(database.read(self.root,'papers.json')[0]['title'],'Updated in database')

    def test_orphan_figure_transaction_rolls_back(self):
        f={'id':'f1','paper_id':'missing','kind':'framework','status':'candidate'}
        with self.assertRaises(sqlite3.IntegrityError):database.write(self.root,'figures.json',[f])
        self.assertEqual(database.read(self.root,'figures.json'),[])

    def test_duplicate_doi_rolls_back(self):
        p={**self.paper,'id':'p2','doi':'10.1/EXAMPLE'}
        with self.assertRaises(sqlite3.IntegrityError):database.write(self.root,'papers.json',[self.paper,p])
        self.assertEqual(len(database.read(self.root,'papers.json')),1)

    def test_referenced_paper_cannot_be_deleted(self):
        f={'id':'f1','paper_id':'p1','kind':'framework','status':'candidate'}
        database.write(self.root,'figures.json',[f])
        with self.assertRaises(sqlite3.IntegrityError):database.write(self.root,'papers.json',[])
        self.assertEqual(len(database.read(self.root,'papers.json')),1)

    def test_bootstrap_is_bounded_and_database_not_public(self):
        (self.root/'site').mkdir();(self.root/'site/index.html').write_text('<html></html>')
        scope={'years':[2025,2026],'venues':[{'id':'ICSE'}]}
        f={'id':'f1','paper_id':'p1','kind':'framework','status':'published','reviewed':False,'publication_verified':True,'caption':'Pipeline','number':'Figure 1','version':'v1','attribution':'An author','license':'CC-BY-4.0','source_url':'https://example.org/paper','rights_url':'https://example.org/license','image':'https://example.org/figure.png'}
        sizes=[]
        for n in [10,5000]:
            papers=[self.paper]+[{**self.paper,'id':f'p{i+2}','doi':f'10.1/p{i+2}','title':'Large metadata '+str(i),'extra':'x'*1000} for i in range(n)]
            payload={'papers.json':papers,'figures.json':[f],'scope.json':scope,'status.json':{}}
            with patch.object(build,'ROOT',self.root),patch.object(build,'read',lambda name:payload[name]):build.main()
            sizes.append((self.root/'dist/catalog.js').stat().st_size)
            self.assertFalse(list((self.root/'dist').rglob('*.sqlite3')))
            self.assertEqual(len(list((self.root/'dist/data').glob('papers-*.json'))),(len(papers)+99)//100)
        self.assertLess(sizes[1],sizes[0]+100)
        self.assertLess(sizes[1],10000)

if __name__=='__main__':unittest.main()
