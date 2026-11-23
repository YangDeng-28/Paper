"""Build bounded first-page payloads from SQLite; never ship the database."""
import copy
import hashlib
import json
import shutil
from pathlib import Path
from common import ROOT, read, validate

PAGE_SIZE=24
SHARD_SIZE=100

def emit(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n','utf-8')

def thumbnail(out,image):
    if not image.startswith('assets/'):return None
    try:
        from PIL import Image,ImageOps
        with Image.open(out/image) as im:
            im=ImageOps.exif_transpose(im);im.thumbnail((720,480))
            target='assets/thumbs/'+hashlib.sha256(image.encode()).hexdigest()[:20]+'.webp'
            (out/target).parent.mkdir(parents=True,exist_ok=True)
            im.convert('RGB').save(out/target,'WEBP',quality=82)
            return target
    except (ImportError,OSError,ValueError):return None

def main():
    papers,figures,scope=read('papers.json'),read('figures.json'),read('scope.json')
    validate(papers,figures,scope)
    papers=sorted(papers,key=lambda p:(p['title'],p['id']))
    papers.sort(key=lambda p:p.get('added_at',''),reverse=True)
    by_id={p['id']:p for p in papers}
    published=sorted([copy.deepcopy(f) for f in figures if f.get('status')=='published'],key=lambda f:(by_id[f['paper_id']]['title'],f['id']))
    published.sort(key=lambda f:f.get('added_at',''),reverse=True)
    by_id={p['id']:p for p in papers};out=ROOT/'dist'
    if out.exists():shutil.rmtree(out)
    shutil.copytree(ROOT/'site',out,ignore=lambda path,names:['figures'] if Path(path).name=='assets' else [])
    for f in published:
        for field in ['image','thumbnail']:
            image=f.get(field,'')
            if image.startswith('assets/'):
                source=ROOT/'site'/image
                assert source.is_file(),'missing figure image: '+image
                target=out/image;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        thumb=thumbnail(out,f['image'])
        if thumb:f['thumbnail']=thumb
    pi,fi=[],[]
    for start in range(0,len(papers),SHARD_SIZE):
        file=f'data/papers-{start//SHARD_SIZE:04d}.json';batch=papers[start:start+SHARD_SIZE]
        emit(out/file,{'papers':batch})
        for p in batch:
            pi.append({k:p.get(k,[] if k in ['authors','tags'] else '') for k in ['id','title','authors','tags','venue','year','added_at']}|{'_file':file})
    for start in range(0,len(published),SHARD_SIZE):
        file=f'data/figures-{start//SHARD_SIZE:04d}.json';batch=published[start:start+SHARD_SIZE]
        emit(out/file,{'figures':batch,'papers':[by_id[i] for i in dict.fromkeys(f['paper_id'] for f in batch)]})
        for f in batch:
            fi.append({k:f.get(k,[] if k=='tags' else '') for k in ['id','paper_id','kind','chart_type','caption','note','tags','reviewed','added_at']}|{'_file':file})
    emit(out/'search-index.json',{'papers':pi,'figures':fi})
    first=published[:PAGE_SIZE];initial_ids=list(dict.fromkeys(f['paper_id'] for f in first))
    coverage=[{'venue':v['id'],'year':y,'papers':sum(p['venue']==v['id'] and p['year']==y for p in papers),'figures':sum(by_id[f['paper_id']]['venue']==v['id'] and by_id[f['paper_id']]['year']==y for f in published)} for v in scope['venues'] for y in scope['years']]
    catalog={'schema_version':2,'scope':scope,'status':read('status.json'),'papers':[by_id[i] for i in initial_ids],
      'figures':first,'totals':{'papers':len(papers),'figures':len(published),'curated':sum(bool(f.get('reviewed')) for f in published)},
      'coverage':coverage,'charts':sorted({f['chart_type'] for f in published if f.get('chart_type')}),
      'paging':{'index':'search-index.json','page_size':PAGE_SIZE,'shard_size':SHARD_SIZE}}
    (out/'catalog.js').write_text('window.CATALOG = '+json.dumps(catalog,ensure_ascii=False,separators=(',',':'))+';\n','utf-8')
    (out/'.nojekyll').touch()
    print(f'Built dist: {len(papers)} papers, {len(published)} public figures; bootstrap {(out/"catalog.js").stat().st_size:,} bytes. SQLite excluded.')

if __name__=='__main__':main()
