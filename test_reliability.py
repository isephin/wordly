from advanced_analyzer import options, run
from file_reader import extract
from io import BytesIO
from zipfile import ZipFile
import csv
from pathlib import Path
from statistics import mean
from math import isclose


def main():
    try:
        options({'case': True, 'stem': True})
    except ValueError:
        pass
    else:
        raise AssertionError('Incompatible settings accepted')
    for workers in (2, 3, 4):
        opt = options({'workers': workers, 'frequency': 2})
        a, _ = run(['Apple apple pear', 'banana'], opt)
        b, _ = run(['Apple apple pear', 'banana'], opt, True)
        assert a == b == {'apple': 2, 'pear': 1, 'banana': 1}
    assert extract('x.csv', b'name,comment\na,apple\nb,pear', '1')[0] == ['apple', 'pear']
    root = Path(__file__).resolve().parent / 'results'
    with (root / 'benchmark_raw.csv').open() as f:
        raw = list(csv.DictReader(f))
    with (root / 'benchmark_summary.csv').open() as f:
        summary = list(csv.DictReader(f))
    assert len(raw) == 40 and len(summary) == 4
    for row in summary:
        trials = [r for r in raw if r['Dataset'] == row['Dataset']]
        assert len(trials) == 10 and all(r['Identical Results'] == 'True' for r in trials)
        s = mean(float(r['Sequential Time (s)']) for r in trials)
        p = mean(float(r['Parallel Time (s)']) for r in trials)
        assert isclose(s, float(row['Mean Sequential (s)']))
        assert isclose(p, float(row['Mean Parallel (s)']))
        assert isclose(s/p, float(row['Speedup']))
        assert isclose(s/p*50, float(row['Efficiency (%)']))
    print('Reliability and archived benchmark checks passed')

if __name__ == '__main__':
    main()
