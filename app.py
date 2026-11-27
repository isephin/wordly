import csv
import json
from threading import Lock
from core.advanced_analyzer import options, run, terms, word_statistics
from core.worker_policy import worker_limit, select_workers
from core.file_reader import extract
from pathlib import Path

from flask import Flask, render_template, request, jsonify

# Create the local Flask server and set upload limits.
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["MAX_FORM_MEMORY_SIZE"] = 100 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["MAX_FORM_PARTS"] = 100
# Only one timed analysis runs at a time to reduce overlapping workloads.
ANALYSIS_LOCK = Lock()
from distributed.distributed_web import bp as distributed_bp
app.config["WORDLY_ANALYSIS_LOCK"] = ANALYSIS_LOCK
app.register_blueprint(distributed_bp)
MAX_LINES = 1_100_000
MAX_CHARS = 60_000_000

BASE = Path(__file__).resolve().parent

DATASETS = {
    "small": "small.txt",
    "medium": "medium.txt",
    "large": "large.txt",
    "extra_large": "extra_large.txt"
}


# Serve the browser interface and available worker limit.
@app.route("/")
def index():
    return render_template("index.html", worker_limit=worker_limit())


# Return spreadsheet headers so users can select a column.
@app.route("/api/columns", methods=["POST"])
def columns():
    try:
        f=request.files['file']
        _, names=extract(f.filename,f.read())
        return jsonify(names)
    except Exception as e:
        return jsonify(error=str(e)),400

# Main analysis endpoint: the browser sends text, files or a dataset and settings.
@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        # Read settings before choosing the actual parallel worker count.
        raw_options=json.loads(request.form.get('options','{}'))
        requested_workers=raw_options.get('workers',2)
        opt=options({**raw_options,'workers':2})
        uploads=[f for f in request.files.getlist('file') if f.filename]
        if len(uploads) > 10:
            raise ValueError("Upload up to 10 files at a time.")
        plain=request.form.get('text','')
        dataset=request.form.get('dataset','')
        docs=[]
        # Convert the chosen source into document names and lists of text lines.
        if plain.strip(): docs=[('Pasted text',plain.splitlines())]
        elif uploads:
            for i,f in enumerate(uploads):
                lines,_=extract(f.filename,f.read(),request.form.get('column_'+str(i),''))
                docs.append((f.filename,lines))
        elif dataset in DATASETS:
            filename=DATASETS[dataset]
            with (BASE / 'datasets' / filename).open(encoding='utf-8') as f:
                docs = [(filename, f.readlines())]
        else: raise ValueError('Choose a source.')
        # Join the documents and remove blank lines before counting.
        lines=[line for _, rows in docs for line in rows if line.strip()]
        if not lines:
            raise ValueError('No text found.')
        if len(lines) > MAX_LINES or sum(map(len, lines)) > MAX_CHARS:
            raise ValueError("Text exceeds the analysis limit (1.1 million lines or 60 million characters).")
        # Choose manual workers or the best measured local calibration.
        n, selection = select_workers(len(lines), requested_workers)
        opt['workers']=n
        # Run the same counting engine sequentially and in parallel.
        # The sequential baseline uses two chunks in one process.
        with ANALYSIS_LOCK:
            seq, st = run(lines, {**opt,'workers':2})
            par, pt = run(lines, opt, True)
        # Rank words by frequency; the minimum count only affects displayed results.
        ranked=sorted(((w,n) for w,n in seq.items() if n>=opt['frequency']),key=lambda x:(-x[1],x[0]))
        words=[dict(word=w,count=n) for w,n in ranked]
        total = sum(seq.values())
        raw, excluded = word_statistics(lines, opt, seq)
        # Search previews are limited to 10,000 lines.
        preview=[dict(original=line[:2000], processed=terms(line[:2000],opt)) for line in lines[:min(10000,len(lines))]]
        # For multiple files, count each document separately for the comparison view.
        comparison=[]
        if len(docs)>1:
            for name,rows in docs:
                c,_=run(rows,opt)
                comparison.append(dict(name=name,total=sum(c.values()), counts=dict(c)))
        # Send the results to JavaScript. Speedup = sequential time / parallel time.
        # Efficiency = speedup / worker count * 100; identical compares all counts.
        return jsonify(
            filename=', '.join((name for name, _ in docs)),
            responses=len(lines),
            total_words=total,
            unique_words=len(seq),
            raw_words=raw,
            excluded_words=excluded,
            characters=sum((len(line.rstrip('\r\n')) for line in lines)),
            sequential=st,
            parallel=pt,
            speedup=st / pt,
            efficiency=st / pt / opt['workers'] * 100,
            identical=seq == par,
            words=words,
            options=opt,
            worker_selection=selection,
            preview=preview,
            comparison=comparison,
        )
    except Exception as e:
        return jsonify(error=str(e)),400

# Read the archived original benchmark results, not live timings.
@app.route("/api/benchmarks")
def benchmarks():
    path = BASE / "results" / "benchmark_summary.csv"

    if not path.exists():
        return jsonify([])

    with path.open(encoding="utf-8") as file:
        return jsonify(list(csv.DictReader(file)))


# Read the recorded final worker-scaling results.
@app.get("/api/benchmarks/scaling")
def scaling_benchmarks():
    path = BASE / "results" / "published" / "scaling_v3_3_summary.csv"
    if not path.exists():
        return jsonify([])
    with path.open(encoding="utf-8", newline="") as file:
        return jsonify(list(csv.DictReader(file)))


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
