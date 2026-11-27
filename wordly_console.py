"""Console interface for the current Wordly counting engine."""
import argparse
import csv
from datetime import datetime
from pathlib import Path

from advanced_analyzer import options, run, word_statistics
from file_reader import extract
from worker_policy import select_workers, worker_limit

ROOT = Path(__file__).resolve().parent
DATASETS = ('small', 'medium', 'large', 'extra_large')
SIZES = (1000, 10000, 100000, 1000000)
MAX_BYTES = 100 * 1024 * 1024


def heading(title):
    print('\n' + '=' * 76)
    print(title)
    print('=' * 76)


def read_file(path, column=None):
    path = Path(path).expanduser()
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('File exceeds 100 MiB.')
    rows, _ = extract(path.name, path.read_bytes(),
                      '' if column is None else str(column))
    return rows


def analyze(lines, settings):
    lines = [line for line in lines if line.strip()]
    if not lines:
        raise ValueError('No text found.')
    if len(lines) > 1_100_000 or sum(map(len, lines)) > 60_000_000:
        raise ValueError('Text exceeds the analysis limit.')
    opt = options({**settings, 'workers': 2})
    n, selection = select_workers(len(lines), settings.get('workers', 'auto'))
    opt['workers'] = n
    print('\n' + selection, flush=True)
    print('Running sequential analysis...', flush=True)
    seq, st = run(lines, {**opt, 'workers': 2})
    print(f'Running parallel analysis with {n} workers...', flush=True)
    par, pt = run(lines, opt, True)
    raw, excluded = word_statistics(lines, opt, seq)
    ranked = sorted(((w, c) for w, c in seq.items() if c >= opt['frequency']),
                    key=lambda item: (-item[1], item[0]))
    return dict(lines=len(lines), raw=raw, excluded=excluded,
                total=sum(seq.values()), unique=len(seq), workers=n,
                sequential=st, parallel=pt, speedup=st / pt,
                efficiency=st / pt / n * 100, identical=seq == par,
                ranked=ranked, options=opt)


def print_results(name, result, top):
    heading('WORD FREQUENCY RESULTS - LIVE RUN')
    print(f'Input: {name}')
    print(f"Nonempty lines: {result['lines']:,}")
    print(f"Raw words: {result['raw']:,}   Excluded: {result['excluded']:,}")
    unit = 'words' if result['options']['ngram'] == 1 else 'phrases'
    print(f"Counted {unit}: {result['total']:,}   Unique {unit}: {result['unique']:,}")
    print(f"\n{'Rank':>4}  {'Term':<30}  {'Frequency':>12}  Relative frequency")
    rows = result['ranked'][:top]
    if not rows:
        print('No terms match the selected filters.')
    else:
        maximum = rows[0][1]
        for i, (term, count) in enumerate(rows, 1):
            label = term if len(term) <= 30 else term[:27] + '...'
            print(f'{i:>4}  {label:<30}  {count:>12,}  ' + '#' * max(1, round(20 * count / maximum)))
    heading('PERFORMANCE COMPARISON')
    print(f"Sequential time : {result['sequential']:.6f} s")
    print(f"Parallel time   : {result['parallel']:.6f} s ({result['workers']} workers)")
    print(f"Speedup         : {result['speedup']:.4f}x")
    print(f"Efficiency      : {result['efficiency']:.2f}%")
    winner = 'Parallel' if result['speedup'] > 1 else 'Sequential' if result['speedup'] < 1 else 'Neither (equal times)'
    print(f'Faster method   : {winner}')
    print('Count agreement : ' + ('PASS - identical full counters' if result['identical'] else 'FAIL - counts differ'))
    print('Live single-run times; file extraction and display are excluded.')


def save_results(name, result):
    folder = ROOT / 'results' / 'runs' / ('console-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True)
    with (folder / 'summary.csv').open('w', encoding='utf-8', newline='') as f:
        fields = ['lines', 'raw', 'excluded', 'total', 'unique', 'workers',
                  'sequential', 'parallel', 'speedup', 'efficiency', 'identical']
        writer = csv.writer(f)
        writer.writerow(['input'] + fields)
        writer.writerow([name] + [result[k] for k in fields])
    with (folder / 'word_counts.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['word_or_phrase', 'count'])
        writer.writerows(result['ranked'])
    with (folder / 'settings.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['setting', 'value'])
        writer.writerows(result['options'].items())
    print(f'\nSaved results to {folder}')


def recorded_rows(choice='best'):
    path = ROOT / 'results' / 'published' / 'scaling_v3_3_summary.csv'
    with path.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    groups = {}
    for row in rows:
        groups.setdefault(int(row['lines']), []).append(row)
    output = []
    for size, group in sorted(groups.items()):
        seq = next(r for r in group if int(r['workers']) == 1)
        candidates = [r for r in group if int(r['workers']) > 1]
        if choice == 'best':
            par = min(candidates, key=lambda r: (float(r['mean_seconds']), int(r['workers'])))
        else:
            par = next((r for r in candidates if r['workers'] == str(choice)), None)
            if par is None:
                raise ValueError('Worker count not present in the recorded benchmark.')
        output.append((size, seq, par))
    return output


def show_benchmarks(choice='best'):
    heading('RECORDED BENCHMARKS - CURRENT ENGINE')
    print('Apple M4 Pro, 14 logical CPUs, eight trials per configuration.')
    print('Synthetic feedback, default filters; recorded averages, not live results.\n')
    print(f"{'Responses':>12} {'Workers':>7} {'Seq (s)':>12} {'Par (s)':>12} {'Speedup':>9} {'Eff. (%)':>9}")
    for size, seq, par in recorded_rows(choice):
        print(f"{size:>12,} {int(par['workers']):>7} {float(seq['mean_seconds']):>12.6f} "
              f"{float(par['mean_seconds']):>12.6f} {float(par['speedup']):>9.3f} {float(par['local_efficiency_percent']):>9.2f}")
    print('\nPublished means use rounded console timings from the completed experiment.')


def settings_from_args(args):
    return dict(workers=args.workers, stop=not args.keep_stop_words,
                case=args.case_sensitive, numbers=args.numbers, stem=args.stem,
                length=args.min_length, frequency=args.min_count,
                ngram=args.ngram, include=args.include, exclude=args.exclude)


def interactive():
    while True:
        heading('wordly. - CONSOLE')
        for i, size in enumerate(SIZES, 1):
            print(f'[{i}] {size:,} sample responses')
        print('[5] Custom document\n[6] Paste text\n[7] Recorded benchmarks\n[0] Exit')
        try:
            choice = input('\nSelect: ').strip()
            if choice == '0':
                return
            if choice == '7':
                show_benchmarks(input('Best or worker count [best]: ').strip().lower() or 'best')
            elif choice in ('1', '2', '3', '4', '5', '6'):
                if choice in ('1', '2', '3', '4'):
                    path = ROOT / 'datasets' / (DATASETS[int(choice) - 1] + '.txt')
                    name, lines = path.name, read_file(path)
                elif choice == '5':
                    path = Path(input('File path: ').strip().strip('\"\'')).expanduser()
                    column = None
                    if path.suffix.lower() in ('.csv', '.xlsx'):
                        value = input('Column number (1 = first, blank = all): ').strip()
                        if value:
                            if int(value) < 1:
                                raise ValueError('Column number must be positive.')
                            column = int(value) - 1
                    name, lines = path.name, read_file(path, column)
                else:
                    print('Paste text. Enter :end on a new line to finish.')
                    lines = []
                    while True:
                        line = input()
                        if line == ':end':
                            break
                        lines.append(line)
                    name = 'Pasted text'
                workers = input(f'Workers (2-{worker_limit()} or auto) [auto]: ').strip().lower() or 'auto'
                result = analyze(lines, {'workers': workers})
                print_results(name, result, 10)
                if result['identical'] and input('\nSave CSV results? [y/N]: ').strip().lower() == 'y':
                    save_results(name, result)
            else:
                print('Invalid selection.')
            input('\nPress Enter to return to the menu...')
        except (EOFError, KeyboardInterrupt):
            print('\nExiting.')
            return
        except (ValueError, OSError, ImportError) as exc:
            print(f'Error: {exc}')


def main():
    parser = argparse.ArgumentParser(description='Wordly console - current analyzer')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--dataset', choices=DATASETS)
    source.add_argument('--file', type=Path)
    source.add_argument('--text')
    source.add_argument('--benchmarks', nargs='?', const='best', choices=['best'] + [str(n) for n in (2, 4, 6, 8, 10, 12, 14)])
    parser.add_argument('--workers', default='auto')
    parser.add_argument('--top', type=int, default=10)
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--column', type=int, help='Spreadsheet column, numbered from 1')
    parser.add_argument('--keep-stop-words', action='store_true')
    parser.add_argument('--case-sensitive', action='store_true')
    parser.add_argument('--numbers', action='store_true')
    parser.add_argument('--stem', action='store_true')
    parser.add_argument('--ngram', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--min-length', type=int, default=1)
    parser.add_argument('--min-count', type=int, default=1)
    parser.add_argument('--include', default='')
    parser.add_argument('--exclude', default='')
    args = parser.parse_args()
    if args.top < 1 or (args.column is not None and args.column < 1):
        parser.error('--top and --column must be positive.')
    if args.column is not None and not args.file:
        parser.error('--column requires --file.')
    try:
        if args.benchmarks:
            show_benchmarks(args.benchmarks)
            return 0
        if args.dataset:
            path = ROOT / 'datasets' / (args.dataset + '.txt')
            name, lines = path.name, read_file(path)
        elif args.file:
            name = args.file.name
            lines = read_file(args.file, None if args.column is None else args.column - 1)
        elif args.text is not None:
            name, lines = 'Pasted text', args.text.splitlines()
        else:
            interactive()
            return 0
        result = analyze(lines, settings_from_args(args))
        print_results(name, result, args.top)
        if not result['identical']:
            return 1
        if args.export:
            save_results(name, result)
        return 0
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
