"""Trusted LAN coordinator; HTTP transport is not encrypted."""
import json, os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from urllib.request import Request, build_opener, ProxyHandler
from urllib.parse import urlsplit

MAX_BYTES = 16 * 1024 * 1024

def configuration():
    urls = [u.strip().rstrip('/') for u in os.environ.get('WORDLY_WORKERS','').split(',') if u.strip()]
    token = os.environ.get('WORDLY_TOKEN','')
    if not 2 <= len(urls) <= 8 or len(set(urls)) != len(urls):
        raise ValueError('Configure 2–8 distinct worker addresses.')
    if len(token) < 24: raise ValueError('Set a shared token of at least 24 characters.')
    for u in urls:
        p = urlsplit(u)
        if p.scheme != 'http' or not p.hostname or p.path or p.query or p.fragment or p.username or p.password:
            raise ValueError('Use HTTP worker addresses, including their ports.')
    return urls, token

def call(url, token, path, payload=None):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    if body is not None and len(body)>MAX_BYTES: raise ValueError('Worker chunk exceeds 16 MiB; use a smaller dataset or more workers.')
    req = Request(url+path, data=body, headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with build_opener(ProxyHandler({})).open(req, timeout=60) as response:
        data = response.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES: raise ValueError('Worker response too large.')
        return json.loads(data)

def batches(lines, opt):
    # Exact UTF-8 JSON size, including separators and options.
    overhead = len(json.dumps({'lines': [], 'options': opt}, ensure_ascii=False).encode('utf-8'))
    limit = min(MAX_BYTES, 4 * 1024 * 1024)
    batch, size = [], overhead
    for line in lines:
        length = len(json.dumps(line, ensure_ascii=False).encode('utf-8'))
        if overhead + length > limit:
            raise ValueError('A single line exceeds the worker batch limit.')
        extra = length + (2 if batch else 0)
        if batch and size + extra > limit:
            yield batch
            batch, size = [], overhead
            extra = length
        batch.append(line)
        size += extra
    if batch:
        yield batch


def distributed_run(lines, opt, urls, token):
    start = perf_counter()
    n = len(urls)
    chunks = [lines[i*len(lines)//n:(i+1)*len(lines)//n] for i in range(n)]
    def job(pair):
        url, chunk = pair
        total = Counter(); elapsed = 0.0; name = None; count = 0; requests = 0
        for batch in batches(chunk, opt):
            result = call(url,token,'/count',{'lines':batch,'options':opt})
            counts = result['counts']
            if not isinstance(counts,dict) or any(not isinstance(k,str) or type(v) is not int or v<0 for k,v in counts.items()): raise ValueError('Invalid worker result.')
            if result['lines'] != len(batch): raise ValueError('Worker line count mismatch.')
            if name is not None and name != result['name']: raise ValueError('Worker identity changed.')
            name = result['name']; total.update(counts); elapsed += result['seconds']; count += len(batch); requests += 1
        return total, {'address':url,'name':name or url,'lines':count,'seconds':elapsed,'batches':requests}
    merged = Counter(); details=[]
    with ThreadPoolExecutor(max_workers=n) as pool:
        for counts, info in pool.map(job,zip(urls,chunks)):
            merged.update(counts); details.append(info)
    return merged, perf_counter()-start, details
