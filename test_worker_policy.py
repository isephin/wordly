from tempfile import TemporaryDirectory
from pathlib import Path
from worker_policy import select_workers, save_profile, worker_limit, SIZES
from advanced_analyzer import options, run

def main():
    with TemporaryDirectory() as tmp:
        p=Path(tmp)/'profile.json'
        assert select_workers(1000,'auto',p)[0]==2
        rows=[]
        high=worker_limit()
        for dataset,size in zip(SIZES,[1000,10000,100000,1000000]):
            times={1:1.0 if size<100000 else 10.0,2:2.0}
            if high>2: times[high]=3.0 if size<100000 else 1.0
            for n,t in times.items(): rows.append([dataset,size,'sequential' if n==1 else f'parallel_{n}',n,5,t,0,0])
        save_profile(rows,'test',5,p)
        assert select_workers(1000,'auto',p)[0]==2
        assert 'sequential' in select_workers(1000,'auto',p)[1]
        assert select_workers(1000000,'auto',p)[0]==high
        assert select_workers(3,high,p)[0]==min(3,high)
        assert options({'workers':high})['workers']==high
        lines=['hello world','hello again']*20
        seq,_=run(lines,options({'workers':2})); par,_=run(lines,options({'workers':high}),True)
        assert seq==par
    print('Calibration, automatic selection, worker limits and exact parallel counts passed.')
if __name__=='__main__': main()
