"""First-party Crossref indexes and USENIX session lists; no bot challenges bypassed."""
import argparse
import html
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlencode,urljoin
from common import read,write,now
from collect import merge
from network import get,get_json

JOURNALS=[('0098-5589',['TSE']),('1049-331X',['TOSEM']),('0164-0925',['TOPLAS']),('1939-1374',['TSC']),('2994-970X',['FSE','ISSTA']),('2475-1421',['PLDI','POPL','OOPSLA'])]
CONFERENCES={
 'ICSE':{2025:'2025 IEEE/ACM 47th International Conference on Software Engineering (ICSE)',2026:'2026 IEEE/ACM 48th International Conference on Software Engineering'},
 'ASE':{2025:'2025 IEEE/ACM 40th International Conference on Automated Software Engineering (ASE)',2026:'2026 IEEE/ACM 41st International Conference on Automated Software Engineering (ASE)'},
 'SOSP':{2025:'Proceedings of the ACM SIGOPS 30th Symposium on Operating Systems Principles',2026:'Symposium on Operating Systems Principles 2026'},
 'FM':{2025:'Formal Methods FM 2025',2026:'Formal Methods FM 2026'},
 'ISSTA':{2025:'Proceedings of the 34th ACM SIGSOFT International Symposium on Software Testing and Analysis',2026:'Proceedings of the International Symposium on Software Testing and Analysis 2026'}
}

def text(value):return html.unescape(re.sub('<[^>]*>','',str(value))).strip()

def published_year(item):
    for field in ('published-print','published','issued','published-online'):
        parts=item.get(field,{}).get('date-parts',[[]])[0]
        if parts:return int(parts[0])
    return 0

def conference_matches(item,venue):
    containers=' '.join(item.get('container-title',[])).lower()
    if any(s in containers for s in ['companion','workshop','doctoral','demonstration','knowledge engineering']):return False
    if venue=='ICSE':return bool(re.search(r'international conference on software engineering(?:\s*\(icse\)|\s*$)',containers))
    if venue=='ASE':return 'conference on automated software engineering' in containers
    if venue=='SOSP':return 'symposium on operating systems principles' in containers
    if venue=='ISSTA':return 'symposium on software testing and analysis' in containers
    if venue=='FM':return any(re.fullmatch(r'(?:fm 202[56]: )?formal methods(?:\s*[–—-]\s*fm 202[56])?',c.lower().strip()) for c in item.get('container-title',[]))
    return False

def normalize(item,venue):
    doi=item['DOI'].lower().strip()
    return {'id':'doi:'+doi,'doi':doi,'title':text(' '.join(item.get('title',[]))),
      'authors':[text(' '.join(filter(None,[a.get('given'),a.get('family')])) or a.get('name','')) for a in item.get('author',[])],
      'venue':venue,'year':published_year(item),'source_url':'https://doi.org/'+doi,'metadata_source':'https://api.crossref.org/works/'+doi,
      'verification':'pending','figure_status':'pending','tags':[],'added_at':now()[:10],
      'crossref_issue':item.get('issue',''),'container_title':item.get('container-title',[]),
      'crossref_license':item.get('license',[]),'crossref_links':item.get('link',[])}

class SessionLinks(HTMLParser):
    def __init__(self,base):super().__init__();self.base=base;self.current=None;self.entries={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and '/presentation/' in attrs.get('href',''):
            self.current=[urljoin(self.base,attrs['href']),[]]
    def handle_data(self,data):
        if self.current:self.current[1].append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.current:
            url,parts=self.current;title=' '.join(''.join(parts).split())
            if title:self.entries[url]=title
            self.current=None

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--venue');ap.add_argument('--year',type=int,choices=[2025,2026]);args=ap.parse_args()
    scope=read('scope.json');allowed={v['id'] for v in scope['venues']}
    if args.venue and args.venue not in allowed:ap.error('unknown venue')
    years=[args.year] if args.year else scope['years'];papers=read('papers.json',[])
    status=read('status.json',{});previous_queries=status.get('queries',[]);previous_errors=status.get('errors',[])
    status.update(last_attempt=now(),errors=[],queries=[],provider='Crossref + USENIX',coverage_complete=False)
    tasks=[]
    for issn,venues in JOURNALS:
        if not args.venue or args.venue in venues:
            for year in years:tasks.append(('journal',issn,venues,year))
    for venue,titles in CONFERENCES.items():
        if not args.venue or venue==args.venue:
            for year in years:tasks.append(('conference',titles[year],[venue],year))
    if not args.venue or args.venue=='OSDI':
        for year in years:tasks.append(('usenix',f'https://www.usenix.org/conference/osdi{str(year)[-2:]}/technical-sessions',['OSDI'],year))
    if args.venue or args.year:
        selected={'/'.join(v)+f'/{y}' for _,_,v,y in tasks}
        status['queries']=[q for q in previous_queries if q['query'] not in selected]
        status['errors']=[q for q in previous_errors if q['query'] not in selected]
    for kind,source,venues,year in tasks:
        label='/'.join(venues)+f'/{year}';accepted=[];fetched=0
        try:
            if kind=='usenix':
                parser=SessionLinks(source);parser.feed(get(source).decode('utf-8'))
                for url,title in parser.entries.items():
                    if f'/osdi{str(year)[-2:]}/presentation/' not in url:continue
                    accepted.append({'id':'usenix:'+url.rsplit('/',1)[-1]+':'+str(year),'title':title,'authors':[],'venue':'OSDI','year':year,'source_url':url,'verification':'pending','figure_status':'pending','tags':[],'added_at':now()[:10],'metadata_source':source})
                fetched=len(parser.entries)
                if not accepted:raise ValueError('no presentation links in session page')
            else:
                cursor='*'
                while True:
                    end=min(f'{year}-12-31',now()[:10])
                    params={'filter':f'from-pub-date:{year}-01-01,until-pub-date:{end}','rows':1000}
                    if kind=='journal':
                        base=f'https://api.crossref.org/journals/{source}/works';params['cursor']=cursor
                    else:
                        base='https://api.crossref.org/works';params['query.container-title']=source
                        params['filter']+=',type:'+('book-chapter' if venues[0]=='FM' else 'proceedings-article')
                    result=get_json(base+'?'+urlencode(params))['message'];items=result.get('items',[]);fetched+=len(items)
                    for item in items:
                        if not item.get('DOI') or not item.get('title') or published_year(item)!=year:continue
                        if kind=='journal':
                            if item.get('type')!='journal-article':continue
                            issue=item.get('issue','').upper()
                            venue=venues[0] if len(venues)==1 else next((v for v in venues if issue.startswith(v)),None)
                            if not venue:continue
                        else:
                            venue=venues[0]
                            if not conference_matches(item,venue):continue
                        if args.venue and venue!=args.venue:continue
                        if re.match(r'^(editorial|preface|front matter|back matter|acknowledg|correction|erratum|retraction)\b',text(item['title'][0]),re.I):continue
                        accepted.append(normalize(item,venue))
                    if kind=='conference' or not items or fetched>=result.get('total-results',0):break
                    next_cursor=result.get('next-cursor')
                    if not next_cursor or next_cursor==cursor:raise ValueError('pagination cursor did not advance')
                    cursor=next_cursor;time.sleep(2)
            papers=merge(papers,accepted);write('papers.json',papers)
            status['queries'].append({'query':label,'provider':kind,'status':'ok','fetched':fetched,'matched':len(accepted),'coverage':'bounded_relevance_query' if kind=='conference' else 'indexed_source'})
            print(f'{label}: {len(accepted)} matched / {fetched} fetched; database {len(papers)}',flush=True)
        except Exception as exc:
            status['errors'].append({'query':label,'error':type(exc).__name__+': '+str(exc)[:250]})
            print(label,'FAILED',str(exc)[:200],flush=True)
        finally:
            write('status.json',status)
        time.sleep(2)
    if not status['errors']:status['last_success']=now()
    status['note']='首轮使用 Crossref 官方索引与 USENIX 官网；会议检索存在提供方覆盖边界，不声称全量。自动发现论文与图表待核验，缺失和失败见采集状态。'
    status['last_finished']=now();write('status.json',status)
    print({'papers':len(papers),'failed_queries':len(status['errors'])},flush=True)

if __name__=='__main__':main()
