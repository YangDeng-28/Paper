import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import common
import build
from collect import merge, matches, normalize
from extract import guess_kind

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.scope = common.read('scope.json')
        self.papers = [{'id':'doi:10.1/fixture','doi':'10.1/fixture','title':'Test research paper','authors':['Test Author'],'venue':'ICSE','year':2025,'source_url':'https://example.org/paper','verification':'research_track_verified','tags':[]}]

    def figure(self):
        return {'id':'test','paper_id':self.papers[0]['id'],'kind':'framework','status':'published','reviewed':True,'publication_verified':True,'caption':'Pipeline','number':'Figure 1','version':'v1','note':'Clear stages','attribution':'Example author','license':'CC-BY-4.0','source_url':'https://example.org/paper','rights_url':'https://example.org/license','image':'assets/figures/example.png'}

    def test_real_catalog_valid(self):
        common.validate(common.read('papers.json'),common.read('figures.json'),self.scope)

    def test_scope_has_all_sources_and_years(self):
        self.assertEqual(len(self.scope['venues']),14)
        self.assertEqual(set(self.scope['years']),{2025,2026})

    def test_doi_dedup_preserves_review(self):
        old = self.papers[0]
        new = copy.deepcopy(old)
        new.update(doi=old['doi'].upper(),verification='pending',tags=[])
        result = merge([old],[new])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['verification'],old['verification'])

    def test_doi_added_later_keeps_existing_id(self):
        old = {'id':'dblp:conf/icse/example','dblp_key':'conf/icse/example','title':'Example','venue':'ICSE','year':2025,'doi':''}
        new = {**old,'id':'doi:10.1/example','doi':'10.1/example'}
        result = merge([old],[new])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['id'],'dblp:conf/icse/example')
        self.assertEqual(result[0]['doi'],'10.1/example')

    def test_unverified_paper_cannot_publish_figures(self):
        papers = copy.deepcopy(self.papers); papers[0]['verification'] = 'pending'
        with self.assertRaises(AssertionError): common.validate(papers,[self.figure()],self.scope)

    def test_curated_figure_requires_reason(self):
        f = self.figure(); f['note'] = ''
        with self.assertRaises(AssertionError): common.validate(self.papers,[f],self.scope)

    def test_source_verified_reference_does_not_claim_curated(self):
        f = self.figure(); f.update(reviewed=False,note='')
        common.validate(self.papers,[f],self.scope)

    def test_pacm_issue_disambiguation(self):
        venue = {'id':'FSE','type':'conference','issue':'FSE'}
        self.assertTrue(matches({'number':'FSE'},venue,'journals/pacmse'))
        self.assertFalse(matches({'number':'ISSTA'},venue,'journals/pacmse'))
        self.assertFalse(matches({},venue,'journals/pacmse'))

    def test_workshop_excluded(self):
        self.assertFalse(matches({'venue':'ICSE Workshops'},{'id':'ICSE','type':'conference'},'conf/icse'))

    def test_unverified_cannot_publish(self):
        f = self.figure(); f['publication_verified'] = False
        with self.assertRaises(AssertionError): common.validate(self.papers,[f],self.scope)

    def test_missing_provenance_cannot_publish(self):
        f = self.figure(); f['rights_url'] = ''
        with self.assertRaises(AssertionError): common.validate(self.papers,[f],self.scope)

    def test_path_traversal_rejected(self):
        f = self.figure(); f['image'] = 'assets/../../secret.txt'
        with self.assertRaises(AssertionError): common.validate(self.papers,[f],self.scope)

    def test_thumbnail_path_validated(self):
        f = self.figure(); f['thumbnail'] = 'javascript:alert(1)'
        with self.assertRaises(AssertionError): common.validate(self.papers,[f],self.scope)

    def test_out_of_scope_year_rejected(self):
        papers = copy.deepcopy(self.papers); papers[0]['year'] = 2024
        with self.assertRaises(AssertionError): common.validate(papers,[],self.scope)

    def test_caption_categories(self):
        self.assertEqual(guess_kind('Figure 1. Overview of the framework.'),'framework')
        self.assertEqual(guess_kind('Figure 4. Performance comparison.'),'experiment')
        self.assertIsNone(guess_kind('Figure 3. Code snippet.'))

    def test_build_excludes_candidate_images(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'site/assets/figures').mkdir(parents=True)
            (root/'site/index.html').write_text('<html></html>')
            (root/'site/assets/figures/unreviewed.png').write_bytes(b'not-published')
            (root/'site/assets/figures/example.png').write_bytes(b'approved-fixture')
            f = self.figure()
            payload = {'papers.json':self.papers,'figures.json':[f],'scope.json':self.scope,'status.json':{}}
            with patch.object(build,'ROOT',root),patch.object(build,'read',lambda name:payload[name]): build.main()
            self.assertTrue((root/'dist/assets/figures/example.png').exists())
            self.assertFalse((root/'dist/assets/figures/unreviewed.png').exists())

    def test_normalize_single_author(self):
        p = normalize({'key':'conf/icse/example','title':'A paper','year':'2025','authors':{'author':{'text':'A. Author'}}},{'id':'ICSE'})
        self.assertEqual(p['authors'],['A. Author'])
        self.assertEqual(p['verification'],'pending')

if __name__ == '__main__': unittest.main()
