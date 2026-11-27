import re
from collections import Counter
from time import perf_counter

STOP_WORDS = set("""
a an the is am are was were be been being
and or but if of at by for with about
to from in on into out up down over under
it its this that these those
i me my we our you your they their
he she his her them us
have has had do does did
will would shall should can could may might
must not no as so than too very
more most some any all
please
""".split())

WORD_PATTERN = re.compile(r"[a-z]+")


def preprocess_text(text):
    words = WORD_PATTERN.findall(text.lower())

    return [
        word for word in words
        if word not in STOP_WORDS
    ]


def count_words(lines):
    frequencies = Counter()

    for line in lines:
        words = preprocess_text(line)
        frequencies.update(words)

    return frequencies


def split_dataset(lines):
    midpoint = (len(lines) + 1) // 2

    return [
        lines[:midpoint],
        lines[midpoint:]
    ]


def sequential_analysis(lines):
    start = perf_counter()

    chunks = split_dataset(lines)
    frequencies = Counter()

    for chunk in chunks:
        frequencies.update(count_words(chunk))

    elapsed = perf_counter() - start

    return frequencies, elapsed


def get_top_words(frequencies, limit=10):
    return sorted(
        frequencies.items(),
        key=lambda item: (-item[1], item[0])
    )[:limit]


def parallel_analysis(lines):
    from concurrent.futures import ProcessPoolExecutor

    start = perf_counter()

    chunks = split_dataset(lines)
    frequencies = Counter()

    with ProcessPoolExecutor(max_workers=2) as executor:
        partial_results = executor.map(count_words, chunks)

        for result in partial_results:
            frequencies.update(result)

    elapsed = perf_counter() - start

    return frequencies, elapsed


def calculate_metrics(sequential_time, parallel_time):
    speedup = sequential_time / parallel_time
    efficiency = (speedup / 2) * 100

    return speedup, efficiency
