"""Validate and build a portable, dependency-free static site."""
import json
import shutil
from pathlib import Path
from common import ROOT, read, validate

def main():
    papers, figures, scope = read('papers.json'), read('figures.json'), read('scope.json')
    validate(papers, figures, scope)
    published = [f for f in figures if f.get('status') == 'published']
    for figure in published:
        if figure['image'].startswith('assets/'):
            assert (ROOT / 'site' / figure['image']).is_file(), 'missing figure image'
    out = ROOT / 'dist'
    if out.exists():
        shutil.rmtree(out)
    # Candidate images must not leak into the public deployment artifact.
    shutil.copytree(ROOT / 'site', out, ignore=lambda path,names: ['figures'] if Path(path).name == 'assets' else [])
    for figure in published:
        for field in ['image', 'thumbnail']:
            image = figure.get(field, '')
            if image.startswith('assets/'):
                target = out / image
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / 'site' / image, target)
    catalog = {'papers': papers, 'figures': published, 'scope': scope, 'status': read('status.json')}
    (out / 'catalog.js').write_text('window.CATALOG = ' + json.dumps(catalog, ensure_ascii=False) + ';\n', 'utf-8')
    (out / '.nojekyll').touch()
    print(f'Built dist: {len(papers)} papers, {len(published)} published figures')

if __name__ == '__main__':
    main()
