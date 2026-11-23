"""Extract figure candidates from a local PDF for a known paper.

Heuristic crops require visual review; they are never automatically curated.
Only approved reusable sources should be supplied. Original PDFs stay in .cache.
"""
import argparse
import hashlib
import re
from pathlib import Path
from common import ROOT, read, write, now

CAPTION = re.compile(r'^(?:Fig(?:ure)?\.?)[\s\u00a0]*(\d+)\s*[:.\s]', re.I)

def guess_kind(caption):
    text = caption.lower()
    if any(t in text for t in ['overview', 'architecture', 'workflow', 'framework', 'pipeline', 'state machine']):
        return 'framework'
    if any(t in text for t in ['performance', 'comparison', 'distribution', 'ablation', 'accuracy', 'results', 'effect', 'coverage', 'time', 'cost']):
        return 'experiment'
    return None

def extract(paper, pdf_path, destination=None):
    import pymupdf as fitz
    destination = destination or ROOT / 'site' / 'assets' / 'figures'
    destination.mkdir(parents=True, exist_ok=True)
    existing = read('figures.json', [])
    known = {f['id'] for f in existing}
    added = []
    with fitz.open(pdf_path) as doc:
        for page_no, page in enumerate(doc):
            blocks = sorted(page.get_text('blocks'), key=lambda b: (b[1], b[0]))
            for b in blocks:
                text = ' '.join(b[4].split())
                match = CAPTION.match(text)
                if not match:
                    continue
                number = match.group(1)
                identifier = hashlib.sha256(f'{paper["id"]}:{page_no}:{number}'.encode()).hexdigest()[:20]
                if identifier in known:
                    continue
                kind = guess_kind(text)
                if not kind:
                    continue
                # Find preceding graphical content; vector drawings are included.
                graphics = []
                for drawing in page.get_drawings():
                    rect = drawing['rect']
                    if rect.y1 <= b[1] + 3 and rect.y1 >= b[1] - page.rect.height * .55 and rect.width > 1 and rect.height > 1:
                        graphics.append(rect)
                for item in page.get_image_info():
                    rect = fitz.Rect(item['bbox'])
                    if rect.y1 <= b[1] + 3 and rect.y1 >= b[1] - page.rect.height * .55:
                        graphics.append(rect)
                if not graphics:
                    continue
                # Prefer graphics horizontally overlapping the caption's column.
                x0, x1 = b[0] - 10, b[2] + 10
                nearby = [g for g in graphics if g.x1 > x0 and g.x0 < x1]
                if not nearby:
                    continue
                union = nearby[0]
                for rect in nearby[1:]:
                    union = union | rect
                crop = fitz.Rect(max(0,min(union.x0,x0)-8), max(0,union.y0-15), min(page.rect.width,max(union.x1,x1)+8), min(page.rect.height,b[3]+4))
                if crop.height < 35 or crop.width < 50:
                    continue
                image_path = destination / (identifier + '.png')
                page.get_pixmap(matrix=fitz.Matrix(2,2), clip=crop, alpha=False).save(image_path)
                figure = {
                    'id': identifier, 'paper_id': paper['id'], 'number': 'Figure ' + number,
                    'kind': kind, 'chart_type': '', 'caption': text, 'note': '',
                    'image': 'assets/figures/' + image_path.name, 'page': page_no + 1,
                    'bbox': list(crop), 'source_url': paper['pdf_url'],
                    'version': '作者公开 PDF，提取日期 ' + now()[:10],
                    'license': paper.get('license','unverified'), 'rights_url': paper.get('rights_url',''),
                    'attribution': ', '.join(paper['authors']) + '. ' + paper['title'] + f'. {paper["venue"]} {paper["year"]}.',
                    'modifications': '从 PDF 渲染并裁剪；包含图注；边界待人工核验。',
                    'status': 'candidate', 'reviewed': False, 'added_at': now()[:10],
                    'tags': [], 'extraction_method': 'caption-graphics-heuristic'
                }
                added.append(figure); known.add(identifier)
    write('figures.json', existing + added)
    return added

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', required=True, help='paper id in data/papers.json')
    parser.add_argument('--pdf', required=True, type=Path)
    args = parser.parse_args()
    paper = next((p for p in read('papers.json') if p['id'] == args.paper), None)
    if not paper:
        parser.error('paper not in catalog')
    if not paper.get('pdf_url'):
        parser.error('paper must have a provenance pdf_url')
    added = extract(paper, args.pdf)
    print(f'{len(added)} candidates extracted. Review with scripts/review.py before publication.')

if __name__ == '__main__':
    main()
