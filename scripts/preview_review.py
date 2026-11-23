"""Generate a local review page; never included in the public dist directory."""
import html
from common import ROOT, read

def main():
    papers = {p['id']:p for p in read('papers.json')}
    figures = [f for f in read('figures.json') if f.get('status') != 'rejected']
    cards=[]
    for f in figures:
        source = f['image']
        if source.startswith('assets/'):
            source = '../../site/' + source
        cards.append('<article><h2>'+html.escape(papers[f['paper_id']]['title'])+'</h2><p>'+html.escape(f['number']+' · '+f['status'])+'</p><img src="'+html.escape(source,quote=True)+'"><p>'+html.escape(f['caption'])+'</p><code>'+html.escape(f['id'])+'</code></article>')
    path=ROOT/'.cache/review/index.html'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>本地审核 · SE Figure Atlas</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:20px;background:#f5f8f6;color:#183d2e}article{background:white;padding:30px;margin:25px 0;border:1px solid #ddd;border-radius:8px}img{max-width:100%;display:block;margin:20px auto}h2{font-size:20px}code{background:#eee;padding:8px;display:block;overflow:auto}</style><h1>本地图表审核</h1><p>核对：图像完整、图注对应、来源版本、展示依据；然后通过 scripts/review.py approve 发布并填写参考理由。此页面不包含在公开网站中。</p>'+''.join(cards)+'</html>','utf-8')
    print(path)

if __name__ == '__main__': main()
