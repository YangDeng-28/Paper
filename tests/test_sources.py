import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_sources import conference_matches, published_year
from extract import CAPTION, caption_blocks

class SourceTests(unittest.TestCase):
    def test_formal_methods_container_aliases(self):
        self.assertTrue(conference_matches({'container-title':['Lecture Notes in Computer Science','Formal Methods']},'FM'))
        self.assertTrue(conference_matches({'container-title':['Formal Methods – FM 2026']},'FM'))
        self.assertFalse(conference_matches({'container-title':['Formal Methods in System Design']},'FM'))

    def test_companion_and_workshop_are_not_main_conference(self):
        for name in ['ICSE Workshops','International Conference on Software Engineering Companion','International Conference on Software Engineering and Knowledge Engineering']:
            self.assertFalse(conference_matches({'container-title':[name]},'ICSE'))

    def test_formal_year_over_online_year(self):
        self.assertEqual(published_year({'published-print':{'date-parts':[[2026]]},'published-online':{'date-parts':[[2025]]}}),2026)

    def test_caption_does_not_match_body_reference(self):
        self.assertIsNone(CAPTION.match('Figure 1 gives an overview of our approach.'))
        self.assertIsNotNone(CAPTION.match('Fig. 1. Overview of the approach.'))
        self.assertIsNotNone(CAPTION.match('Figure 2: Results.'))

    def test_caption_stops_before_merged_body(self):
        import pymupdf
        with pymupdf.open() as doc:
            page=doc.new_page()
            page.insert_text((50,100),'Fig. 1. Overview of the approach.',fontsize=9)
            page.insert_text((50,114),'Following body paragraph.',fontsize=11)
            captions=list(caption_blocks(page))
            self.assertEqual(len(captions),1)
            self.assertNotIn('Following',captions[0][4])

if __name__=='__main__':unittest.main()
