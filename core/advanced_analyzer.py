"""Word counting with configurable filters."""
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from time import perf_counter
from core.analyzer import STOP_WORDS
from functools import lru_cache
from core.worker_policy import worker_limit

# Load the optional stemmer once per process, only if requested.
@lru_cache(maxsize=1)
def stemmer():
    from nltk.stem import SnowballStemmer
    return SnowballStemmer("english")

def options(raw):
    # Keep the shared engine settings valid. The console uses the defaults
    # below and lets the user choose the number of workers.
    if not isinstance(raw, dict):
        raise ValueError("Settings must be an object.")
    if raw.get("case") and raw.get("stem"):
        raise ValueError("Choose either case sensitivity or grouping word forms, not both.")

    def number(key, default, low, high):
        return max(low, min(high, int(raw.get(key, default))))

    return dict(
        stop=bool(raw.get('stop', True)),
        case=bool(raw.get('case', False)),
        numbers=bool(raw.get('numbers', False)),
        stem=bool(raw.get('stem', False)),
        length=number('length', 1, 1, 100),
        frequency=number('frequency', 1, 1, 100000000),
        ngram=number('ngram', 1, 1, 3),
        workers=number('workers', 2, 2, worker_limit()),
        exclude=str(raw.get('exclude', '')),
        include=str(raw.get('include', '')),
    )

def tokens(text, opt):
    # The regular expression extracts words without punctuation or underscores.
    # Digits are excluded by default, and words are converted to lowercase.
    pattern = r'[^\W_]+' if opt['numbers'] else r'[^\W\d_]+'
    return re.findall(pattern, text if opt['case'] else text.lower())

def terms(text, opt):
    # Helper for applying the same filters to a single line of text.
    normalize = lambda w: stemmer().stem(w) if opt['stem'] else w
    excluded = {normalize(w) for w in tokens(opt['exclude'], opt)}
    included = {normalize(w) for w in tokens(opt['include'], opt)}
    return list(_terms(text, opt, excluded, included))

def _terms(text, opt, excluded, included):
    # Apply the filters to each token. The default ngram of 1 counts words.
    # An ngram of 2 or 3 can count phrases in the shared engine.
    window = []
    for word in tokens(text, opt):
        term = stemmer().stem(word) if opt['stem'] else word
        if (
            (opt['stop'] and word.lower() in STOP_WORDS)
            or len(word) < opt['length']
            or term in excluded
            or (included and term not in included)
        ):
            # Do not join words across a token rejected by these filters.
            window.clear()
            continue
        window.append(term)
        if len(window) == opt['ngram']:
            yield ' '.join(window)
            window.pop(0)

def count_chunk(payload):
    # A job contains the assigned lines and the selected settings.
    lines, opt = payload
    excluded = {
        stemmer().stem(w) if opt['stem'] else w
        for w in tokens(opt['exclude'], opt)
    }
    included = {
        stemmer().stem(w) if opt['stem'] else w
        for w in tokens(opt['include'], opt)
    }

    # Each job has its own counter, so workers do not write to shared counts.
    # Counter.update adds the occurrences found in each line (map step).
    counts = Counter()
    for line in lines:
        counts.update(_terms(line, opt, excluded, included))
    return counts

def run(lines, opt, parallel=False):
    # Time partitioning, counting, merging and process management together.
    start = perf_counter()
    n = opt['workers']

    # Data decomposition: split lines into n nearly equal, nonoverlapping chunks.
    # For example, 1,000 lines with 4 workers gives 4 chunks of 250 lines.
    # Integer division also covers all lines when the sizes are uneven.
    chunks = [
        lines[i * len(lines) // n : (i + 1) * len(lines) // n]
        for i in range(n)
    ]
    jobs = [(chunk, opt) for chunk in chunks]
    counts = Counter()

    if parallel:
        # Separate processes can count different chunks at the same time.
        # Spawn starts fresh Python processes on each supported OS.
        with ProcessPoolExecutor(
            max_workers=n, mp_context=get_context('spawn')
        ) as pool:
            for result in pool.map(count_chunk, jobs):
                # Reduce: add each worker's partial counter to the total.
                counts.update(result)
    else:
        # One process counts the chunks in order using the same map function.
        for job in jobs:
            counts.update(count_chunk(job))

    return counts, perf_counter() - start


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
