"""Select workers using local timings with default filters."""
import json, math, os, platform, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / 'results' / 'runs' / 'worker_profile.json'
SIZES = ('small', 'medium', 'large', 'extra_large')

def worker_limit():
    return max(2, min(14, os.cpu_count() or 2))

def fingerprint():
    return [platform.node(), platform.system(), platform.machine(), os.cpu_count(), list(sys.version_info[:3])]

def save_profile(rows, source, trials, path=PROFILE):
    if trials < 5: raise ValueError('Calibration requires at least five trials.')
    groups = {}
    for dataset, lines, method, workers, ntrials, seconds, *_ in rows:
        if method == 'network': continue
        if ntrials != trials or seconds <= 0 or not math.isfinite(seconds): raise ValueError('Invalid timing.')
        groups.setdefault(dataset, {'lines':lines,'times':{}})['times'][str(workers)] = seconds
    if set(groups) != set(SIZES): raise ValueError('Calibration requires all four sample datasets.')
    for g in groups.values():
        if '1' not in g['times'] or len(g['times']) < 2: raise ValueError('Missing sequential or parallel timings.')
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps({'machine':fingerprint(),'trials':trials,'source':str(source),'groups':groups},indent=2),encoding='utf-8'); tmp.replace(path)

def select_workers(lines, requested, path=PROFILE):
    if lines < 1: raise ValueError('No text found.')
    limit=min(worker_limit(),max(2,lines))
    if str(requested) != 'auto':
        try: n=int(requested)
        except (ValueError,TypeError): raise ValueError('Choose Auto or a valid worker count.')
        if not 2<=n<=worker_limit(): raise ValueError(f'Choose 2–{worker_limit()} workers.')
        return min(n,limit), 'Manual selection.' if n<=limit else f'Reduced to {limit} workers for this workload.'
    try:
        profile=json.loads(path.read_text(encoding='utf-8'))
        if profile['machine'] != fingerprint(): raise ValueError('Different machine')
        group=min(profile['groups'].values(), key=lambda g: abs(math.log(lines/g['lines'])))
        times={int(n):float(t) for n,t in group['times'].items() if 1<=int(n)<=limit and float(t)>0 and math.isfinite(float(t))}
        parallel=min((n for n in times if n>=2),key=lambda n:(times[n],n))
        best=min(times,key=lambda n:(times[n],n))
        fastest='sequential' if best==1 else f'{best} parallel workers'
        return parallel, f'Auto: {parallel} parallel workers; fastest measured method was {fastest} at {group["lines"]:,} sample lines. Estimate for default filters only.'
    except (OSError,ValueError,TypeError,KeyError,ZeroDivisionError,AttributeError):
        return 2, 'Auto: no matching local calibration; using 2 workers for comparison.'
