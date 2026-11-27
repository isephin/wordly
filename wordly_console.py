# wordly. - Word Frequency Analyzer
# PDC final project: Cinco, Estorninos, Guevarra (BCS44)
# Both methods count the same input. Only the way work is assigned differs.

# Standard library tools for text processing, files, and sample generation.
import os
import re
import random
import csv
import io
import json
import zipfile
from pathlib import Path
# Counter stores each word and its frequency.
from collections import Counter
# Separate processes allow CPU-bound counting to run on multiple cores.
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
# A high-resolution timer measures elapsed processing time.
from time import perf_counter
from functools import lru_cache
from statistics import mean


# 1. Settings and text preprocessing

SIZES = (1000, 10000, 100000, 1000000)


# Keep the worker count between 2 and 14, based on detected logical CPUs.
def worker_limit():
    return max(2, min(14, os.cpu_count() or 2))


# Common words removed by default.
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


# Load the optional stemmer only when word-form grouping is requested.
# Cache it so we do not create a new stemmer for every word.
@lru_cache(maxsize=1)
def stemmer():
    from nltk.stem import SnowballStemmer
    return SnowballStemmer("english")


def options(raw):
    # Keep the shared engine settings valid. The console uses the defaults
    # below and lets the user choose the number of workers and stop word removal.
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


# 2. Sequential and parallel word counting


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
    # Include partitioning, counting, merging, and process overhead in the timer.
    start = perf_counter()
    n = opt['workers']
    total_lines = len(lines)
    chunks = []

    # Data decomposition: split the input into nearly equal line ranges.
    # Example: 1,000 lines and 4 workers produce 4 chunks of 250 lines.
    # Integer division also covers every line when the sizes are uneven.
    for i in range(n):
        first = i * total_lines // n
        last = (i + 1) * total_lines // n
        chunks.append(lines[first:last])

    jobs = [(chunk, opt) for chunk in chunks]
    counts = Counter()

    if parallel:
        # Multiprocessing: separate Python processes can count at the same time.
        # Spawn starts fresh Python processes and works on different operating systems.
        with ProcessPoolExecutor(
            max_workers=n, mp_context=get_context('spawn')
        ) as pool:
            # pool.map assigns jobs to workers and returns their partial counters.
            for result in pool.map(count_chunk, jobs):
                # Reduce step: add the partial counts to the final counter.
                counts.update(result)
    else:
        # Sequential: the main process handles each job one after another.
        # It uses the same counting function and merging logic as parallel mode.
        for job in jobs:
            counts.update(count_chunk(job))

    return counts, perf_counter() - start


# 3. Reading text and documents


SUPPORTED = {'.txt', '.md', '.csv', '.xlsx', '.pdf', '.docx', '.json'}


def extract(name, data, column=''):
    # Choose a reader based on the file extension.
    # All supported formats are converted into a list of text lines.
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError('Unsupported file type: ' + ext)

    # DOCX and XLSX are compressed files. Check their expanded size first.
    if ext in {'.docx', '.xlsx'}:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 150 * 1024 * 1024:
                raise ValueError('Document expands beyond the supported size.')

    if ext in {'.txt', '.md'}:
        return data.decode('utf-8-sig').splitlines(), []

    if ext == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        lines = []
        for page in reader.pages:
            lines.extend((page.extract_text() or '').splitlines())
        if not any(x.strip() for x in lines):
            raise ValueError('No extractable PDF text; scanned PDFs require OCR.')
        return lines, []

    if ext == '.docx':
        from docx import Document
        doc = Document(io.BytesIO(data))
        lines = [p.text for p in doc.paragraphs]
        lines.extend(c.text for t in doc.tables for r in t.rows for c in r.cells)
        return lines, []

    if ext == '.json':
        # Visit nested lists and objects, keeping only string values.
        def strings(v):
            if isinstance(v, str):
                yield v
            elif isinstance(v, list):
                for x in v:
                    yield from strings(x)
            elif isinstance(v, dict):
                for x in v.values():
                    yield from strings(x)
        return list(strings(json.loads(data.decode('utf-8-sig')))), []

    # CSV and XLSX share the same table reader. XLSX uses the active sheet.
    if ext == '.csv':
        rows = csv.reader(io.StringIO(data.decode('utf-8-sig')))
    else:
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        try:
            return table(book.active.values, column)
        finally:
            book.close()
    return table(rows, column)


def table(rows, column):
    # Treat the first row as the header and read the remaining rows as data.
    rows = iter(rows)
    header = next(rows, [])
    names = [f'{i+1}: {str(v or "Column "+str(i+1))}' for i, v in enumerate(header)]
    index = int(column) if column else None
    if index is not None and not 0 <= index < len(names):
        raise ValueError('Invalid column')

    lines = []
    for row in rows:
        values = row if index is None else row[index:index+1]
        lines.extend(str(v) for v in values if v is not None and str(v).strip())
    return lines, names


# 4. Sample datasets


# Synthetic campus feedback templates, not responses from actual students.
positive = [
    "The speaker explained the topic clearly.",
    "The seminar was informative and engaging.",
    "The registration process was smooth and organized.",
    "The venue was comfortable and spacious.",
    "The organizers were approachable and helpful.",
    "The activities encouraged student participation.",
    "The workshop provided useful practical knowledge.",
    "The presentation materials were easy to understand.",
    "The event was well organized.",
    "The speakers shared relevant experiences.",
    "The discussion was interesting and educational.",
    "The event schedule was followed properly.",
    "The technical team handled the equipment well.",
    "The workshop helped me develop new skills.",
    "The question and answer session was helpful."
]

negative = [
    "The registration process took too long.",
    "The venue was too crowded.",
    "The microphone was difficult to hear.",
    "The seminar started later than expected.",
    "The presentation was difficult to follow.",
    "The internet connection was unstable.",
    "The room temperature was uncomfortable.",
    "The speakers had limited time for discussion.",
    "The instructions were unclear.",
    "The activities felt rushed.",
    "The seating arrangement was inconvenient.",
    "The event schedule was confusing.",
    "The sound system needs improvement.",
    "The workshop lacked practical examples.",
    "The waiting time was too long."
]

suggestions = [
    "Please provide more interactive activities.",
    "The organizers should improve the registration system.",
    "A larger venue would be better.",
    "More time should be given for questions.",
    "Please invite more industry professionals.",
    "The event should include more practical demonstrations.",
    "Provide clearer instructions before the seminar.",
    "Improve the sound system for future events.",
    "Please distribute the presentation materials.",
    "The organizers should announce the schedule earlier.",
    "Include more activities for student participation.",
    "Provide longer breaks between sessions.",
    "Improve communication with the participants.",
    "More workshops should be conducted in the future.",
    "Please consider providing additional seating."
]

def generate_feedback(rng):
    # Randomly select a category using fixed weights, then pick a template.
    category = rng.choices(
        ["positive", "negative", "suggestion", "mixed"],
        weights=[40, 20, 20, 20],
        k=1
    )[0]

    if category == "positive":
        return rng.choice(positive)
    elif category == "negative":
        return rng.choice(negative)
    elif category == "suggestion":
        return rng.choice(suggestions)
    else:
        return (
            rng.choice(positive) + " " +
            rng.choice(suggestions)
        )


def sample_lines(size):
    # Keep the same seed and dataset order as the web application.
    rng = random.Random(42)
    for n in SIZES:
        if n == size:
            return [generate_feedback(rng) + '\n' for _ in range(n)]
        # Advance the random generator through earlier dataset sizes so
        # selecting one dataset produces the same text as the web generator.
        for _ in range(n):
            generate_feedback(rng)
    raise ValueError('Invalid dataset size.')


# 5. Performance comparison


def analyze(lines, workers, trials=1, remove_stop_words=True):
    # Remove blank lines and reject empty or oversized inputs before timing.
    lines = [line for line in lines if line.strip()]
    if not lines:
        raise ValueError('No text found.')
    if len(lines) > 1_100_000 or sum(map(len, lines)) > 60_000_000:
        raise ValueError('Text exceeds the analysis limit.')
    # Do not request more workers than needed for the number of lines.
    workers = min(workers, max(2, len(lines)))
    # Apply the same stop word setting to both counting methods.
    opt = options({'workers': workers, 'stop': remove_stop_words})
    seq_times, par_times = [], []
    reference = None
    for trial in range(trials):
        print(f'Running trial {trial + 1}/{trials} ({workers} parallel workers)...', flush=True)
        # The sequential baseline uses two chunks but only one process.
        # Parallel mode uses the selected number of worker processes.
        # Alternate execution order to reduce repeated order effects.
        if trial % 2 == 0:
            seq, st = run(lines, {**opt, 'workers': 2})
            par, pt = run(lines, opt, True)
        else:
            par, pt = run(lines, opt, True)
            seq, st = run(lines, {**opt, 'workers': 2})
        # Check the entire counter before reporting performance.
        if seq != par or (reference is not None and seq != reference):
            raise RuntimeError('Word counts do not match.')
        reference = seq
        seq_times.append(st)
        par_times.append(pt)
    # Get the average time across all trials.
    st, pt = mean(seq_times), mean(par_times)
    # Speedup = sequential time / parallel time.
    # Above 1 means parallel was faster; below 1 means sequential was faster.
    # For small inputs, starting and coordinating processes can cost more
    # time than the parallel counting saves.
    speedup = st / pt
    # Efficiency = speedup / number of parallel workers * 100.
    # It measures speedup relative to the worker count, not CPU utilization.
    return {'lines': len(lines), 'workers': workers, 'sequential': st,
            'parallel': pt, 'speedup': speedup,
            'efficiency': speedup / workers * 100,
            'counts': reference, 'trials': trials,
            'stop_words_removed': remove_stop_words}


# 6. Displaying results and saving graphs


def top_words(result):
    # Sort by highest count first, then alphabetically when counts tie.
    return sorted(result['counts'].items(), key=lambda pair: (-pair[1], pair[0]))[:10]


def print_results(result):
    print('\n' + '=' * 65)
    print('TOP 10 MOST FREQUENT WORDS')
    print('=' * 65)
    print(f"{'Rank':>4}  {'Word':<30} {'Frequency':>12}")
    for i, (word, count) in enumerate(top_words(result), 1):
        print(f'{i:>4}  {word:<30} {count:>12,}')
    print(f"\nTotal counted words: {sum(result['counts'].values()):,}")
    print(f"Unique words: {len(result['counts']):,}")
    print('\nPERFORMANCE COMPARISON (LIVE)')
    print(f"Input lines     : {result['lines']:,}")
    print(f"Parallel workers: {result['workers']}")
    print(f"Trials          : {result['trials']}")
    print("Stop words      : " + ("Removed" if result['stop_words_removed'] else "Included"))
    print(f"Sequential time : {result['sequential']:.6f} seconds")
    print(f"Parallel time   : {result['parallel']:.6f} seconds")
    print(f"Speedup         : {result['speedup']:.4f}x")
    print(f"Efficiency      : {result['efficiency']:.2f}%")
    print('Faster method   : ' + ('Parallel' if result['speedup'] > 1 else 'Sequential' if result['speedup'] < 1 else 'Equal'))
    print('Verification    : Both methods produced identical word counts.')


def plot_results(results):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('Install matplotlib to generate graphs: python -m pip install matplotlib')
        return
    # Save plots as PNG so they also work in a terminal without a display.
    folder = Path('wordly_results')
    folder.mkdir(exist_ok=True)
    # Show the top words for the last dataset analyzed.
    result = results[-1]
    top = top_words(result)
    fig, ax = plt.subplots(figsize=(8, 4))
    if top:
        ax.barh([w for w, _ in reversed(top)], [n for _, n in reversed(top)])
    else:
        ax.text(0.5, 0.5, 'No matching words', ha='center', transform=ax.transAxes)
    ax.set(title='Top 10 words', xlabel='Frequency')
    fig.tight_layout()
    path = folder / 'word_frequency.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    paths = [path]
    # Compare measured sequential and parallel times side by side.
    labels = [f"{r['lines']:,}" for r in results]
    x = list(range(len(results)))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - .18 for i in x], [r['sequential'] for r in results], .36, label='Sequential')
    ax.bar([i + .18 for i in x], [r['parallel'] for r in results], .36, label='Parallel')
    ax.set_xticks(x, labels)
    ax.set(xlabel='Input lines', ylabel='Mean time (seconds)', title='Execution time')
    if len(results) > 1:
        ax.set_yscale('log')
    ax.legend()
    fig.tight_layout()
    path = folder / 'execution_time.png'
    fig.savefig(path, dpi=150)
    plt.close(fig)
    paths.append(path)
    # When comparing datasets, also show speedup and efficiency.
    if len(results) > 1:
        for field, label, filename in [('speedup', 'Speedup', 'speedup.png'),
                                       ('efficiency', 'Efficiency (%)', 'efficiency.png')]:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.bar(labels, [r[field] for r in results])
            ax.set(xlabel='Input lines', ylabel=label, title=label)
            if field == 'speedup':
                ax.axhline(1, linestyle='--', color='gray')
            fig.tight_layout()
            path = folder / filename
            fig.savefig(path, dpi=150)
            plt.close(fig)
            paths.append(path)
    print('\nGraphs saved in:', folder.resolve())
    # Display the same images inline when running in a notebook.
    try:
        from IPython import get_ipython
        from IPython.display import display, Image
        if getattr(get_ipython(), 'kernel', None) is not None:
            for path in paths:
                display(Image(filename=str(path)))
    except ImportError:
        pass


# 7. Console menu and user input


def read_workers():
    value = input(f'Parallel workers (2-{worker_limit()}) [2]: ').strip()
    workers = int(value or '2')
    if not 2 <= workers <= worker_limit():
        raise ValueError(f'Choose 2-{worker_limit()} workers.')
    return workers


def read_stop_words():
    # Keep the original benchmark filters unless the user chooses otherwise.
    while True:
        value = input("Remove stop words? (Y/n) [Y]: ").strip().lower()
        if value in ("", "y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("Please enter Y or N.")


def main():
    while True:
        print('\n' + '=' * 65)
        print('wordly. - WORD FREQUENCY ANALYZER')
        print('=' * 65)
        for i, size in enumerate(SIZES, 1):
            print(f'[{i}] {size:,} sample responses')
        print('[5] Custom text file or document')
        print('[6] Paste text')
        print('[7] Compare all four datasets')
        print('[0] Exit')
        try:
            choice = input('\nSelect: ').strip()
            if choice == '0':
                break
            if choice not in ('1', '2', '3', '4', '5', '6', '7'):
                print('Invalid selection.')
                continue
            workers = read_workers()
            remove_stop_words = read_stop_words()
            if choice == '7':
                # Use the same worker count and stop word setting for all four datasets.
                trials = int(input('Trials per dataset [1]: ').strip() or '1')
                if not 1 <= trials <= 8:
                    raise ValueError('Choose 1-8 trials.')
                results = []
                for size in SIZES:
                    print(f'\nDataset: {size:,} responses', flush=True)
                    results.append(analyze(sample_lines(size), workers, trials, remove_stop_words))
                print(f"\n{'Lines':>10} {'Workers':>8} {'Seq (s)':>12} {'Par (s)':>12} {'Speedup':>9} {'Eff. (%)':>9}")
                for r in results:
                    print(f"{r['lines']:>10,} {r['workers']:>8} {r['sequential']:>12.6f} {r['parallel']:>12.6f} {r['speedup']:>9.3f} {r['efficiency']:>9.2f}")
                print("Stop words: " + ("Removed" if remove_stop_words else "Included"))
                print('All word counts match.')
            else:
                if choice in ('1', '2', '3', '4'):
                    lines = sample_lines(SIZES[int(choice) - 1])
                elif choice == '5':
                    path = Path(input('File path: ').strip().strip('"\'')).expanduser()
                    if path.stat().st_size > 100 * 1024 * 1024:
                        raise ValueError('File exceeds 100 MiB.')
                    lines, _ = extract(path.name, path.read_bytes())
                else:
                    lines = []
                    print('Enter text. Type :end on a new line to finish.')
                    while True:
                        line = input()
                        if line == ':end':
                            break
                        lines.append(line)
                result = analyze(lines, workers, remove_stop_words=remove_stop_words)
                print_results(result)
                results = [result]
            plot_results(results)
        except (ValueError, OSError, ImportError, RuntimeError) as exc:
            print('Error:', exc)
        except (EOFError, KeyboardInterrupt):
            break
    print('Exiting Wordly.')


# The main guard prevents spawned workers from opening the menu again.
if __name__ == '__main__':
    main()
