"""Configurable analysis; original benchmark engine is intentionally unchanged."""
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from time import perf_counter
from analyzer import STOP_WORDS
from functools import lru_cache
from worker_policy import worker_limit

@lru_cache(maxsize=1)
def stemmer():
    from nltk.stem import SnowballStemmer
    return SnowballStemmer("english")

def options(raw):
    if not isinstance(raw, dict):
        raise ValueError("Settings must be an object.")
    if raw.get("case") and raw.get("stem"):
        raise ValueError("Choose either case sensitivity or grouping word forms, not both.")
    def number(key, default, low, high):
        return max(low, min(high, int(raw.get(key, default))))
    return dict(stop=bool(raw.get('stop', True)), case=bool(raw.get('case', False)), numbers=bool(raw.get('numbers', False)), stem=bool(raw.get('stem', False)), length=number('length',1,1,100), frequency=number('frequency',1,1,100000000), ngram=number('ngram',1,1,3), workers=number('workers',2,2,worker_limit()), exclude=str(raw.get('exclude','')), include=str(raw.get('include','')))

def tokens(text, opt):
    pattern = r'[^\W_]+' if opt['numbers'] else r'[^\W\d_]+'
    return re.findall(pattern, text if opt['case'] else text.lower())

def terms(text, opt):
    normalize = lambda w: stemmer().stem(w) if opt['stem'] else w
    excluded = {normalize(w) for w in tokens(opt['exclude'], opt)}
    included = {normalize(w) for w in tokens(opt['include'], opt)}
    return list(_terms(text,opt,excluded,included))

def _terms(text,opt,excluded,included):
    window=[]
    for word in tokens(text,opt):
        term=stemmer().stem(word) if opt['stem'] else word
        if (opt['stop'] and word.lower() in STOP_WORDS) or len(word)<opt['length'] or term in excluded or (included and term not in included):
            window.clear() # phrases never bridge filtered words
            continue
        window.append(term)
        if len(window)==opt['ngram']:
            yield ' '.join(window)
            window.pop(0)

def count_chunk(payload):
    lines,opt=payload
    excluded={stemmer().stem(w) if opt['stem'] else w for w in tokens(opt['exclude'],opt)}
    included={stemmer().stem(w) if opt['stem'] else w for w in tokens(opt['include'],opt)}
    counts=Counter()
    for line in lines:
        counts.update(_terms(line,opt,excluded,included))
    return counts

def run(lines,opt,parallel=False):
    start=perf_counter()
    n=opt['workers']; chunks=[lines[i*len(lines)//n:(i+1)*len(lines)//n] for i in range(n)]
    jobs=[(chunk,opt) for chunk in chunks]; counts=Counter()
    if parallel:
        with ProcessPoolExecutor(max_workers=n,mp_context=get_context('spawn')) as pool:
            for result in pool.map(count_chunk,jobs): counts.update(result)
    else:
        for job in jobs: counts.update(count_chunk(job))
    return counts,perf_counter()-start


def word_statistics(lines, opt, counts):
    """Count words before and after input filters, independently of phrase size.

    With numbers disabled, digit runs are counted as excluded input units;
    adjacent letter runs are counted separately, matching the tokenizer.
    Minimum count is a display filter and does not affect these totals.
    """
    if opt['numbers']:
        raw = sum(len(tokens(line, opt)) for line in lines)
    else:
        pattern = re.compile(r'[^\W\d_]+|\d+')
        raw = sum(len(pattern.findall(line if opt['case'] else line.lower()))
                  for line in lines)
    retained = (sum(counts.values()) if opt['ngram'] == 1 else
                sum(count_chunk((lines, {**opt, 'ngram': 1})).values()))
    return raw, raw - retained
