"""Publish, recrop, reject, or list figure candidates. Changes are local until git push."""
import argparse
from common import ROOT, read, write, validate, now

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list','approve','reject','crop'])
    parser.add_argument('id', nargs='?')
    parser.add_argument('--note')
    parser.add_argument('--kind', choices=['framework','experiment'])
    parser.add_argument('--chart-type')
    parser.add_argument('--license')
    parser.add_argument('--rights-url')
    parser.add_argument('--pdf')
    parser.add_argument('--bbox', nargs=4, type=float, metavar=('X0','Y0','X1','Y1'))
    args = parser.parse_args()
    figures = read('figures.json')
    if args.action == 'list':
        for f in figures:
            print(f'{f["id"]}\t{f["status"]}\t{f["kind"]}\t{f["number"]}\t{f["caption"][:100]}')
        return
    figure = next((f for f in figures if f['id'] == args.id), None)
    if figure is None:
        parser.error('unknown figure id')
    if args.action == 'reject':
        figure.update(status='rejected', reviewed=False)
    elif args.action == 'crop':
        if not args.pdf or not args.bbox:
            parser.error('crop requires --pdf and --bbox x0 y0 x1 y1 (PDF points)')
        import pymupdf as fitz
        with fitz.open(args.pdf) as doc:
            page = doc[figure['page'] - 1]
            box = fitz.Rect(args.bbox)
            if box.is_empty or not page.rect.contains(box):
                parser.error('crop is empty or outside page')
            page.get_pixmap(matrix=fitz.Matrix(2,2),clip=box,alpha=False).save(ROOT/'site'/figure['image'])
        figure.update(bbox=args.bbox, reviewed=False, status='candidate', modifications='人工调整 PDF 裁剪区域；待重新审核。')
    else:
        if not args.note:
            parser.error('approval requires a useful --note describing visual reference value')
        for field, value in [('kind',args.kind),('chart_type',args.chart_type),('license',args.license),('rights_url',args.rights_url)]:
            if value:
                figure[field] = value
        if figure.get('license') in (None, '', 'unverified'):
            parser.error('confirm reuse basis with --license and --rights-url before approval')
        figure.update(status='published',publication_verified=True,reviewed=True,note=args.note,reviewed_at=now(),modifications='PDF 渲染与裁剪；已人工核验边界。')
        validate(read('papers.json'),figures,read('scope.json'))
    write('figures.json',figures)
    print(f'{figure["id"]}: {figure["status"]}. Rebuild the site to apply changes.')

if __name__ == '__main__':
    main()
