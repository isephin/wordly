from flask import Blueprint, jsonify, render_template, request
from advanced_analyzer import options, run
from distributed import configuration, distributed_run, call
from pathlib import Path
from worker_policy import worker_limit, select_workers

bp=Blueprint('distributed',__name__)
@bp.get('/distributed')
def page(): return render_template('distributed.html', worker_limit=worker_limit())
@bp.get('/api/distributed/workers')
def workers():
    try:
        urls,token=configuration(); out=[]
        for url in urls:
            try: out.append(dict(address=url,name=call(url,token,'/health')['name'],online=True))
            except Exception: out.append(dict(address=url,online=False))
        return jsonify(out)
    except ValueError as e: return jsonify(error=str(e)),400
@bp.post('/api/distributed/analyze')
def analyze():
    try:
        from flask import current_app
        urls,token=configuration(); data=request.get_json()
        if not isinstance(data,dict): raise ValueError('Invalid input.')
        dataset=data.get('dataset',''); plain=data.get('text','')
        if plain.strip(): lines=plain.splitlines()
        elif dataset in ('small','medium','large','extra_large'):
            lines=(Path(__file__).resolve().parent/'datasets'/ (dataset+'.txt')).read_text(encoding='utf-8').splitlines()
        else: raise ValueError('Choose text or a sample dataset.')
        lines=[x for x in lines if x.strip()]
        n, selection=select_workers(len(lines),data.get('local_workers',len(urls)))
        opt=options({'workers':n})
        if len(lines)<max(len(urls),n) or len(lines)>1_100_000 or sum(map(len,lines))>60_000_000: raise ValueError('Invalid workload size.')
        with current_app.config["WORDLY_ANALYSIS_LOCK"]:
            seq,st=run(lines,{**opt,'workers':2}); par,pt=run(lines,opt,True); dist,dt,details=distributed_run(lines,opt,urls,token)
        return jsonify(lines=len(lines),local_workers=n,selection=selection,sequential=st,parallel=pt,distributed=dt,workers=details,identical=seq==par==dist,words=[{'word':w,'count':n} for w,n in sorted(seq.items(),key=lambda x:(-x[1],x[0]))[:10]])
    except Exception as e: return jsonify(error=str(e)),400
