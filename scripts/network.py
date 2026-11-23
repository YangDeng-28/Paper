"""Bounded, rate-conscious HTTP access. ATLAS_DIRECT=1 is an optional local routing choice."""
import json
import os
import time
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError,URLError

def get(url,timeout=40,max_bytes=30_000_000):
    opener=build_opener(ProxyHandler({})) if os.environ.get('ATLAS_DIRECT')=='1' else build_opener()
    for attempt in range(4):
        try:
            with opener.open(Request(url,headers={'User-Agent':'SE-Figure-Atlas/0.2 (https://github.com/YangDeng-28/Paper)'}),timeout=timeout) as response:
                if response.status != 200:raise ValueError(f'HTTP {response.status}: expected a successful data response')
                data=response.read(max_bytes+1)
                if len(data)>max_bytes:raise ValueError('response exceeds size limit')
                return data
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==3:raise
            delay=exc.headers.get('Retry-After','')
            time.sleep(float(delay) if delay.isdigit() else 5*(attempt+1))
        except (URLError,TimeoutError,ConnectionError):
            if attempt==3:raise
            time.sleep(2*(attempt+1))

def get_json(url):
    data=get(url)
    if data.lstrip().startswith(b'<'):
        raise ValueError('provider returned HTML instead of JSON; challenge page is not processed')
    return json.loads(data)
