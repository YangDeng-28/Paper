"""Resolve reusable PDFs and extract candidates, with bounded retries and size limits.

Crossref supplies metadata, not a guarantee that an individual image has no
third-party credits. Human review remains mandatory before publishing images.
"""
import argparse
import hashlib
import ipaddress
import json
import socket
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from common import ROOT, read, write, now, https
from extract import extract

LICENSES = {
    'https://creativecommons.org/licenses/by/4.0': 'CC-BY-4.0',
    'https://creativecommons.org/licenses/by/3.0': 'CC-BY-3.0',
    'https://creativecommons.org/publicdomain/zero/1.0': 'CC0-1.0'
}

def public_url(url):
    if not https(url):
        raise ValueError('only public HTTPS sources are accepted')
    parsed = urlparse(url)
    if parsed.port not in (None,443):
        raise ValueError('non-standard source port')
    addresses = socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('source resolves to a non-public address')

class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def download(url, max_bytes=30_000_000):
    public_url(url)
    req = Request(url,headers={'User-Agent':'SE-Figure-Atlas/0.1 (research figure catalog)'})
    with build_opener(Redirects()).open(req,timeout=40) as response:
        chunks, size = [], 0
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise ValueError('download exceeds configured size limit')
            chunks.append(chunk)
        return b''.join(chunks)

def crossref_pdf(paper):
    if not paper.get('doi'):
        return False
    url = 'https://api.crossref.org/works/' + quote(paper['doi'],safe='')
    record = json.loads(download(url,2_000_000))['message']
    licensed_versions = {}
    for license in record.get('license',[]):
        normalized = license.get('URL','').replace('http://','https://').rstrip('/')
        start = license.get('start',{}).get('timestamp',0)
        if normalized in LICENSES and start <= datetime.now(timezone.utc).timestamp() * 1000:
            licensed_versions[license.get('content-version','unspecified')] = LICENSES[normalized]
    for link in record.get('link',[]):
        version = link.get('content-version','unspecified')
        if link.get('content-type') != 'application/pdf' or version not in licensed_versions:
            continue
        if not https(link.get('URL','')):
            continue
        paper.update(pdf_url=link['URL'],license=licensed_versions[version],rights_url=url)
        return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=20)
    parser.add_argument('--retry',action='store_true')
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    papers = read('papers.json')
    state = read('harvest.json',{})
    cache = ROOT / '.cache' / 'pdf'
    cache.mkdir(parents=True,exist_ok=True)
    attempts = 0
    for paper in papers:
        previous = state.get(paper['id'],{})
        if previous.get('status') == 'extracted':
            continue
        if previous.get('attempt') and not args.retry:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(previous['attempt'])
            if age < timedelta(days=7):
                continue
        if attempts >= args.limit:
            break
        attempts += 1
        current = {'attempt':now()}
        try:
            if not (paper.get('pdf_url') and paper.get('license') in LICENSES.values() and paper.get('rights_url')):
                if not crossref_pdf(paper):
                    current.update(status='awaiting_source',message='No version-matched reusable PDF found; add a verified author source manually.')
                    continue
            path = cache / (hashlib.sha256(paper['id'].encode()).hexdigest() + '.pdf')
            if not path.exists():
                data = download(paper['pdf_url'])
                if not data.lstrip().startswith(b'%PDF-'):
                    raise ValueError('source did not return a PDF')
                path.write_bytes(data)
            added = extract(paper,path)
            current.update(status='extracted',candidates=len(added))
            paper['figure_status'] = 'awaiting_review' if added else 'manual_extraction_needed'
        except Exception as exc:
            current.update(status='failed',message=type(exc).__name__ + ': ' + str(exc)[:250])
        finally:
            state[paper['id']] = current
            write('papers.json',papers)
            write('harvest.json',state)
            print(paper['id'],current['status'])

if __name__ == '__main__':
    main()
