"""Separate exploratory scaling experiment; never overwrites baseline CSVs."""
import argparse, csv, os, platform, sys
from datetime import datetime
from pathlib import Path
from statistics import mean
from advanced_analyzer import options, run
from distributed import configuration, distributed_run
from worker_policy import worker_limit, save_profile, SIZES

def main():
    p=argparse.ArgumentParser(); p.add_argument('--workers',nargs='+',type=int,default=[n for n in (2,4,6,8,10,12,14) if n<=worker_limit()]); p.add_argument('--trials',type=int,default=5); p.add_argument('--datasets',nargs='+',choices=['small','medium','large','extra_large'],default=['small','medium','large','extra_large']); p.add_argument('--network',action='store_true'); p.add_argument('--calibrate',action='store_true'); a=p.parse_args()
    if not 1<=a.trials<=30 or not a.workers or len(set(a.workers))!=len(a.workers) or any(not 2<=n<=worker_limit() for n in a.workers): p.error(f'Choose unique worker counts 2–{worker_limit()} and 1–30 trials.')
    if a.calibrate and (a.network or set(a.datasets)!=set(SIZES) or len(a.datasets)!=4 or a.trials<5): p.error('Calibration requires all four datasets, at least five trials, and no --network.')
    urls,token=configuration() if a.network else ([],None)
    if a.network and len(urls) not in a.workers: p.error('Include the network worker count in --workers for a matched-count comparison.')
    methods=['sequential']+[f'parallel_{n}' for n in a.workers]+(['network'] if a.network else [])
    root=Path(__file__).resolve().parent; out=root/'results'/'runs'/('scaling-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')); out.mkdir(parents=True)
    (out/'environment.txt').write_text(f'{platform.platform()}\nPython {sys.version}\nLogical CPUs: {os.cpu_count()}\nNetwork addresses: {urls}\nTrials: {a.trials}\nRotating execution order; each parallel run starts a fresh pool; network workers already running.\n')
    raw=[]; summary=[]
    with (out/'raw.csv').open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(['dataset','lines','trial','order','method','workers','seconds','identical'])
        for dataset in a.datasets:
            lines=[x for x in (root/'datasets'/f'{dataset}.txt').read_text(encoding='utf-8').splitlines() if x.strip()]
            if len(lines)<max(a.workers): raise ValueError('Too few lines for worker count')
            reference,_=run(lines,options({'workers':2})); times={m:[] for m in methods}
            for trial in range(a.trials):
                offset=trial%len(methods); order=methods[offset:]+methods[:offset]
                for position,m in enumerate(order,1):
                    if m=='sequential': n=1; counts,t=run(lines,options({'workers':2}))
                    elif m=='network': n=len(urls); counts,t,_=distributed_run(lines,options({'workers':n}),urls,token)
                    else: n=int(m.split('_')[1]); counts,t=run(lines,options({'workers':n}),True)
                    equal=counts==reference; writer.writerow([dataset,len(lines),trial+1,position,m,n,t,equal]); f.flush()
                    if not equal: raise RuntimeError('Count mismatch; see raw.csv')
                    times[m].append(t); print(f'{dataset:12} trial {trial+1} {m:12} {t:.6f}s',flush=True)
            base=mean(times['sequential'])
            for m in methods:
                n=1 if m=='sequential' else len(urls) if m=='network' else int(m.split('_')[1]); avg=mean(times[m]); speed=base/avg; summary.append([dataset,len(lines),m,n,a.trials,avg,speed,speed/n*100 if m!='network' else ''])
    with (out/'summary.csv').open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(['dataset','lines','method','workers','trials','mean_seconds','speedup','local_efficiency_percent']); writer.writerows(summary)
    if a.calibrate:
        save_profile(summary, out.name, a.trials)
        print('Local automatic worker profile saved.')
    print('Results:',out)
if __name__=='__main__': main()
