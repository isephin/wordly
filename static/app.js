let selected = "small";
let analyzing = false;

function clearDatasetSelection() {
    document.querySelectorAll(".dataset").forEach(button => {
        button.classList.remove("active");
    });
}

const $ = id => document.getElementById(id);
const format = n => Number(n).toLocaleString("en-US");
const colors = [
    "#b7a1ef", "#91b9f0", "#e8bd79",
    "#e599ac", "#a8d2bd"
];

document.querySelectorAll(".dataset").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".dataset").forEach(b => {
            b.classList.remove("active");
        });

        button.classList.add("active");
        selected = button.dataset.value;
        $("plain-text").value = "";
        updateTextCount();

        $("file").value = ""; $("columns").replaceChildren(); columnGeneration++; if(!analyzing) $("analyze").disabled=false;
        $("file-label").textContent = "＋ Upload files";
    });
});

$("file").addEventListener("change", () => {
    const file = $("file").files[0];

    if (file) {
        $("file-label").textContent = Array.from($("file").files).map(f=>f.name).join(", ");
        loadColumns();
        $("plain-text").value = "";
        updateTextCount();
        selected = "";
        document.querySelectorAll(".dataset").forEach(b => {
            b.classList.remove("active");
        });
    }
});

function bar(label, value, max, display, color) {
    const row = document.createElement("div");
    row.className = "bar-row";

    const name = document.createElement("span");
    name.textContent = label;

    const track = document.createElement("div");
    track.className = "bar-track";

    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${max ? value / max * 100 : 0}%`;

    if (color) fill.style.background = color;

    const number = document.createElement("span");
    number.className = "bar-value";
    number.textContent = display;

    track.appendChild(fill);
    row.append(name, track, number);

    return row;
}

function renderResults(data) {
    $("results").hidden = false;
    current = data; page = 0;
    $("word-search").value=""; $("context-search").value=""; $("copy-export").textContent="Copy";
    const phrases=Number(data.options.ngram)>1;
    $('total-words').previousElementSibling.textContent=phrases?'Phrases counted':'Words counted';
    $('unique-words').previousElementSibling.textContent=phrases?'Unique phrases':'Unique words';

    $("result-source").textContent =
        `${data.filename}`;

    $("responses").textContent = format(data.responses);
    $("total-words").textContent = format(data.total_words);
    $("unique-words").textContent = format(data.unique_words);

    $("speedup").textContent = data.speedup.toFixed(3) + "×";
    $("efficiency").textContent = data.efficiency.toFixed(2) + "%";

    const winner = data.parallel < data.sequential
        ? "Parallel"
        : data.parallel > data.sequential
            ? "Sequential"
            : "Equal";

    $("winner").textContent = winner;

    $("word-cloud").replaceChildren();
    $("word-bars").replaceChildren();
    $("time-bars").replaceChildren();

    const maxWord = data.words.length
        ? data.words[0].count
        : 1;

    data.words.slice(0,10).forEach((item, index) => {
        const word = document.createElement("span");

        word.textContent = item.word;
        word.style.fontSize =
            `${16 + item.count / maxWord * 38}px`;

        word.style.color = colors[index % colors.length];
        word.title = `${format(item.count)} occurrences`;

        $("word-cloud").appendChild(word);

        $("word-bars").appendChild(
            bar(
                item.word,
                item.count,
                maxWord,
                format(item.count)
            )
        );
    });

    if (!data.words.length) {
        $("word-cloud").textContent =
            "No words matched your filters.";
    }

    const maxTime = Math.max(
        data.sequential,
        data.parallel
    );

    $("time-bars").appendChild(
        bar(
            "Sequential",
            data.sequential,
            maxTime,
            data.sequential.toFixed(6) + " s",
            "linear-gradient(90deg,#63577f,#b8a0ed)"
        )
    );

    $("time-bars").appendChild(
        bar(
            "Parallel",
            data.parallel,
            maxTime,
            data.parallel.toFixed(6) + " s",
            "linear-gradient(90deg,#3d7895,#b6dbb0)"
        )
    );

    if (winner === "Parallel") {
        const reduction =
            (1 - data.parallel / data.sequential) * 100;

        $("explanation").textContent =
            `Parallel processing reduced execution time by ${
                reduction.toFixed(2)
            }%. `;

    } else if (winner === "Sequential") {
        $("explanation").textContent =
            "Sequential was faster in this run. Starting and coordinating extra processes takes time.";

    } else {
        $("explanation").textContent =
            "Both methods recorded equal execution times.";
    }

    $("verification").textContent = data.identical
        ? "✓ Both methods returned the same counts."
        : "✕ Verification failed — word frequencies differ.";

    $("verification").style.color =
        data.identical ? "#b6dbb0" : "#ef827a";

    refreshExtras(); recordHistory(data);
    $("results").scrollIntoView({behavior: "smooth"});
}

$("analyze").addEventListener("click", async () => {
    const form = new FormData();

    form.append("dataset", selected);
    form.append("options", JSON.stringify(readOptions()));

    if ($("plain-text").value.trim()) {
        form.append("text", $("plain-text").value);
    }

    if (!$("plain-text").value.trim() && $("file").files[0]) {
        Array.from($("file").files).forEach((f,i)=>{form.append("file",f); const c=$("column-"+i); if(c) form.append("column_"+i,c.value);});
    }

    analyzing = true;
    $("analyze").disabled = true;
    $("analyze").textContent = "Processing...";
    $("status").textContent =
        "Running sequential and parallel word frequency analysis.";

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            body: form
        });

        if (response.status === 413) {
            throw new Error("File exceeds the 100 MB request limit.");
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Analysis failed.");
        }

        renderResults(data);
        $("status").textContent = "Analysis complete.";

    } catch (error) {
        $("status").textContent = error.message;

    } finally {
        analyzing = false;
        $("analyze").disabled = false;
        $("analyze").textContent = "Analyze ↗";
    }
});

async function loadBenchmarks() {
    try {
        const response = await fetch("/api/benchmarks");
        const rows = await response.json();

        if (!rows.length) {
            $("benchmark-graph").textContent =
                "No recorded benchmark results found.";
            return;
        }

        const max = Math.max(
            ...rows.flatMap(row => [
                Number(row["Mean Sequential (s)"]),
                Number(row["Mean Parallel (s)"])
            ])
        );

        rows.forEach(row => {
            const size = format(row.Responses);
            const seq = Number(row["Mean Sequential (s)"]);
            const par = Number(row["Mean Parallel (s)"]);

            const tr = document.createElement("tr");

            [
                size,
                seq.toFixed(6) + " s",
                par.toFixed(6) + " s",
                Number(row.Speedup).toFixed(4) + "×",
                Number(row["Efficiency (%)"]).toFixed(2) + "%"
            ].forEach(value => {
                const td = document.createElement("td");
                td.textContent = value;
                tr.appendChild(td);
            });

            $("benchmark-table").appendChild(tr);

            const group = document.createElement("div");
            group.style.marginBottom = "25px";

            const title = document.createElement("p");
            title.textContent = size + " responses";

            group.append(
                title,
                bar(
                    "Sequential", seq, max,
                    seq.toFixed(4) + " s"
                ),
                bar(
                    "Parallel", par, max,
                    par.toFixed(4) + " s",
                    "linear-gradient(90deg,#3d7895,#b6dbb0)"
                )
            );

            $("benchmark-graph").appendChild(group);
        });

    } catch (error) {
        $("benchmark-graph").textContent =
            "Unable to load benchmark results.";
    }
}

loadBenchmarks();


function updateTextCount() {
    const length = $("plain-text").value.length;
    $("text-count").textContent =
        format(length) + " characters";
}

function restoreDefaultDataset() {
    selected = "small";
    clearDatasetSelection();
    document.querySelector('[data-value="small"]')
        .classList.add("active");
}

$("plain-text").addEventListener("input", () => {
    updateTextCount();

    if ($("plain-text").value.trim()) {
        clearDatasetSelection();
        selected = "";
        $("file").value = ""; $("columns").replaceChildren(); columnGeneration++; if(!analyzing) $("analyze").disabled=false;
        $("file-label").textContent = "＋ Upload files";
    } else {
        restoreDefaultDataset();
    }
});

$("clear-text").addEventListener("click", () => {
    $("plain-text").value = "";
    $("file").value = ""; $("columns").replaceChildren(); columnGeneration++; if(!analyzing) $("analyze").disabled=false;
    $("file-label").textContent = "＋ Upload files";
    updateTextCount();
    restoreDefaultDataset();
    $("plain-text").focus();
});


function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(
        "http://www.w3.org/2000/svg", tag
    );

    Object.entries(attributes).forEach(([key, value]) => {
        element.setAttribute(key, value);
    });

    return element;
}

function svgText(parent, text, attributes) {
    const node = svgElement("text", attributes);
    node.textContent = text;
    parent.appendChild(node);
    return node;
}

const spectralColors = [
    "#6998fa",
    "#ab89ed",
    "#e48bab",
    "#ef9275",
    "#efcd68"
];

function addParticle(svg, path, color, duration, delay) {
    if (window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches) return;

    const particle = svgElement("circle", {
        r: 2.5,
        fill: color,
        class: "light-particle"
    });

    const motion = svgElement("animateMotion", {
        dur: duration,
        begin: delay,
        repeatCount: "indefinite",
        path: path
    });

    particle.appendChild(motion);
    svg.appendChild(particle);
}

function animateHero() {
    const svg = $("spectrum-visual");

    if (!svg) return;

    svg.querySelectorAll(".wave").forEach((path, index) => {
        const curve = path.getAttribute("d");

        for (let i = 0; i < 3; i++) {
            addParticle(
                svg,
                curve,
                spectralColors[(i + index) % 5],
                `${6 + index * 2}s`,
                `${-i * 2}s`
            );
        }
    });
}

function buildFrequencyGraph(words, id) {
    const items = words.slice(0, 5);

    const wrapper = document.createElement("div");
    wrapper.className = "frequency-visual";

    if (!items.length) {
        wrapper.textContent =
            "No words matched your filters.";
        return wrapper;
    }

    const svg = svgElement("svg", {
        viewBox: "0 0 900 340",
        role: "img",
        "aria-label": "Top word frequencies by rank"
    });

    const maximum = Math.max(
        ...items.map(item => item.count)
    );

    const left = 90;
    const right = 810;
    const top = 55;
    const bottom = 265;

    const points = items.map((item, i) => ({
        word: item.word,
        count: item.count,
        color: spectralColors[i],
        x: items.length === 1
            ? 450
            : left + i * (right - left) /
                (items.length - 1),
        y: bottom - item.count / maximum *
            (bottom - top)
    }));

    const defs = svgElement("defs");

    const gradient = svgElement("linearGradient", {
        id: `${id}-gradient`
    });

    spectralColors.forEach((color, index) => {
        gradient.appendChild(svgElement("stop", {
            offset: `${index * 25}%`,
            "stop-color": color
        }));
    });

    defs.appendChild(gradient);

    const filter = svgElement("filter", {
        id: `${id}-blur`,
        x: "-100%",
        y: "-100%",
        width: "300%",
        height: "300%"
    });

    filter.appendChild(svgElement("feGaussianBlur", {
        stdDeviation: 30
    }));

    defs.appendChild(filter);
    svg.appendChild(defs);

    // Background grid: actual frequency values.
    const ticks = [...new Set(
        Array.from({length: 5}, (_, i) =>
            Math.round(maximum * i / 4)
        )
    )];

    ticks.forEach(value => {
        const y = bottom -
            value / maximum * (bottom - top);

        svg.appendChild(svgElement("line", {
            x1: 65,
            y1: y,
            x2: 850,
            y2: y,
            class: "frequency-grid"
        }));

        svgText(svg, format(value), {
            x: 57,
            y: y + 4,
            "text-anchor": "end",
            class: "axis-label"
        });
    });

    // Glow radius and intensity depend on word count.
    points.forEach(point => {
        const ratio = point.count / maximum;

        svg.appendChild(svgElement("circle", {
            cx: point.x,
            cy: point.y,
            r: 18 + ratio * 40,
            fill: point.color,
            opacity: 0.25 + ratio * 0.25,
            filter: `url(#${id}-blur)`,
            class: "data-glow"
        }));
    });

    // Smooth curve connecting actual frequency points.
    let curve = `M ${points[0].x} ${points[0].y}`;

    for (let i = 1; i < points.length; i++) {
        const a = points[i - 1];
        const b = points[i];
        const mid = (a.x + b.x) / 2;

        curve += ` C ${mid} ${a.y},
            ${mid} ${b.y}, ${b.x} ${b.y}`;
    }

    if (points.length > 1) {
        const area = curve +
            ` L ${points[points.length - 1].x} ${bottom}` +
            ` L ${points[0].x} ${bottom} Z`;

        svg.appendChild(svgElement("path", {
            d: area,
            fill: `url(#${id}-gradient)`,
            opacity: ".06",
            class: "frequency-area"
        }));

        svg.appendChild(svgElement("path", {
            d: curve,
            fill: "none",
            stroke: `url(#${id}-gradient)`,
            "stroke-width": "1.8",
            pathLength: "1",
            class: "frequency-line"
        }));

        for (let i = 0; i < 3; i++) {
            addParticle(
                svg,
                curve,
                spectralColors[i],
                "7s",
                `${-i * 2.3}s`
            );
        }
    }

    points.forEach((point, i) => {
        const group = svgElement("g", {
            class: "frequency-node",
            style: `animation-delay: ${i * 120}ms`
        });

        const title = svgElement("title");
        title.textContent =
            `${point.word}: ${format(point.count)} occurrences`;

        group.appendChild(title);

        group.appendChild(svgElement("line", {
            x1: point.x,
            y1: point.y,
            x2: point.x,
            y2: bottom,
            class: "frequency-guide"
        }));

        group.appendChild(svgElement("circle", {
            cx: point.x,
            cy: point.y,
            r: 3 + 5 * Math.sqrt(
                point.count / maximum
            ),
            fill: point.color,
            class: "node-halo"
        }));

        group.appendChild(svgElement("circle", {
            cx: point.x,
            cy: point.y,
            r: 2 + 3 * Math.sqrt(
                point.count / maximum
            ),
            fill: "#fff"
        }));

        const shortWord = point.word.length > 15
            ? point.word.slice(0, 13) + "..."
            : point.word;

        svgText(group, shortWord, {
            x: point.x,
            y: point.y - 20,
            "text-anchor": "middle",
            class: "data-word"
        });

        svgText(group, format(point.count), {
            x: point.x,
            y: point.y + 25,
            "text-anchor": "middle",
            class: "data-count"
        });

        svgText(group, `0${i + 1}`, {
            x: point.x,
            y: 290,
            "text-anchor": "middle",
            class: "axis-label"
        });

        svg.appendChild(group);
    });

    svgText(svg, "WORD RANK", {
        x: 450,
        y: 325,
        "text-anchor": "middle",
        class: "axis-title"
    });

    wrapper.appendChild(svg);

    const caption = document.createElement("div");
    caption.className = "frequency-caption";
    caption.textContent = "Top words · Number of occurrences";
    wrapper.appendChild(caption);

    return wrapper;
}

function updateSpectrum(words) {
    const hero = document.querySelector(".hero .spectrum");



    $("result-spectrum").replaceChildren(
        buildFrequencyGraph(words, "result-frequency")
    );
}

animateHero();
let current=null, page=0, columnGeneration=0;
$('opt-stem').addEventListener('change', () => { if ($('opt-stem').checked) $('opt-case').checked = false; });
$('opt-case').addEventListener('change', () => { if ($('opt-case').checked) $('opt-stem').checked = false; });
function readOptions(){const out={}; for(const k of ['stop','case','numbers','stem','length','frequency','ngram','workers','exclude','include']){const e=$('opt-'+k);out[k]=e.type==='checkbox'?e.checked:e.value;} return out;}
$('reset-options').onclick=()=>{for(const [k,v] of Object.entries({stop:true,case:false,numbers:false,stem:false,length:1,frequency:1,ngram:1,workers:2,exclude:'',include:''})){const e=$('opt-'+k);if(e.type==='checkbox')e.checked=v;else e.value=v;}};
async function loadColumns(){const generation=++columnGeneration;const files=Array.from($('file').files); $('columns').replaceChildren(); $('analyze').disabled=true;try{for(const [i,f] of files.entries()){if(!/\.(csv|xlsx)$/i.test(f.name))continue;const body=new FormData();body.append('file',f);const r=await fetch('/api/columns',{method:'POST',body});const names=await r.json();if(generation!==columnGeneration||$('file').files[i]?.name!==f.name)return;if(!r.ok)throw Error(names.error);const label=document.createElement('label');label.textContent=f.name+' · column ';const select=document.createElement('select');select.id='column-'+i;select.add(new Option('All columns',''));names.forEach((name,index)=>select.add(new Option(name,index)));label.appendChild(select);$('columns').appendChild(label);}}catch(e){$('status').textContent=e.message;}finally{if(generation===columnGeneration&&!analyzing)$('analyze').disabled=false;}}
function refreshExtras(){if(!current)return; const d=current; $('extra-stats').replaceChildren();for(const [label,value] of [['Total words',format(d.raw_words)],['Characters (no line breaks)',format(d.characters)],['Words excluded',format(d.excluded_words)]]){const div=document.createElement('div'), l=document.createElement('span'),v=document.createElement('strong');l.textContent=label;v.textContent=value;div.append(l,v);$('extra-stats').append(div);} $('live-config').textContent=`${d.options.workers} parallel workers · ${["", "Single words", "Two-word phrases", "Three-word phrases"][Number(d.options.ngram)]}. Benchmarks use the original settings. ${d.worker_selection||""}`;renderVisual();renderTable();showContext(false);renderComparison();}
function renderVisual(){
    if(!current)return;
    const items=current.words.slice(0,Number($('top-limit').value));
    const max=items[0]?.count||1;
    const phrase=Number(current.options.ngram)>1;
    $('result-spectrum').replaceChildren(); $('aura-view').replaceChildren();
    $('word-cloud').replaceChildren(); $('word-bars').replaceChildren();
    $('bars-heading').hidden=false; $('png-export').disabled=!items.length;
    if(!items.length){for(const id of ['result-spectrum','aura-view','word-cloud','word-bars'])$(id).textContent='No words found.';return;}
    updateSpectrum(items);
    const cap=$('result-spectrum').querySelector('.frequency-caption');
    if(cap)cap.textContent='Number of times each '+(phrase?'phrase':'word')+' appears';
    layoutClusters(items);
    items.forEach(w=> $('word-bars').append(bar(w.word,w.count,max,format(w.count))));
}

// Place larger words near the centre, then pack smaller words around them.
function layoutClusters(items) {
    if(!items.length)return;
    const maximum = Math.max(1,...items.map(w=>w.count));
    renderCircleMap(items, maximum);
    for (const kind of ['cloud']) {
        const host=$(kind==='aura'?'aura-view':'word-cloud');
        host.replaceChildren();
        const width=host.clientWidth || 320;
        const aura=kind==='aura';
        const factor=Math.min(1.45,width/650);
        const density=items.length>20?.75:items.length>10?.88:1;
        const measure=document.createElement('canvas').getContext('2d');
        const placed=[];
        const pad=16;
        items.forEach((item,i)=>{
            const ratio=item.count/maximum;
            const font=Math.max(13,(aura?14+13*Math.sqrt(ratio):13+42*Math.sqrt(ratio))*factor*density);
            measure.font=`400 ${font}px Helvetica Neue, Arial, sans-serif`;
            const tw=Math.min(width-2*pad,measure.measureText(item.word).width+16);
            const diameter=(aura?142:0)*Math.sqrt(ratio)*factor*density;
            const w=Math.min(width-2*pad,Math.max(tw+(aura?34:12),diameter,40));
            const rows=Math.max(1,Math.ceil(measure.measureText(item.word).width/Math.max(1,w-16)));
            const h=aura?Math.max(font*(rows*1.2+2.2)+18,diameter*.76):font*1.35*rows+12;
            let point=null;
            // Deterministic spiral, with collision checks for readable labels.
            for(let k=0;k<7000;k++){
                const angle=k*2.3999632297;
                const r=6.5*Math.sqrt(k);
                const x=width/2+Math.cos(angle)*r*2.45;
                const y=Math.sin(angle)*r*.82;
                if(x-w/2<pad||x+w/2>width-pad)continue;
                if(placed.every(p=>Math.abs(p.x-x)>=(p.w+w)/2+(aura?18:8)||Math.abs(p.y-y)>=(p.h+h)/2+(aura?18:8))) {point={x,y,w,h};break;}
            }
            if(!point){point={x:width/2,y:Math.max(0,...placed.map(p=>p.y+p.h/2))+h/2+12,w,h};}
            placed.push(point);
            const node=document.createElement('div');
            node.className=aura?'packed-aura':'packed-word';
            node.style.setProperty('--ink',colors[i%colors.length]);
            node.style.setProperty('--glow-size',`${diameter}px`);
            node.style.setProperty('--delay',`${-i*1.27}s`);
            node.style.fontSize=font+'px';
            node.style.width=w+'px';node.style.height=h+'px';
            node.title=`${item.word}: ${format(item.count)}`;
            
            const label=document.createElement('div');label.className='packed-label';
            const word=document.createElement('span');word.textContent=item.word;label.append(word);
            if(aura){const count=document.createElement('small');count.textContent=format(item.count);label.append(count);}
            node.append(label);host.append(node);point.node=node;
        });
        const low=Math.min(...placed.map(p=>p.y-p.h/2));
        const high=Math.max(...placed.map(p=>p.y+p.h/2));
        const margin=aura?24:22;
        const minX=Math.min(...placed.map(p=>p.x-p.w/2));
        const maxX=Math.max(...placed.map(p=>p.x+p.w/2));
        const shift=(width-minX-maxX)/2;
        host.style.height=Math.ceil(high-low+2*margin)+'px';
        placed.forEach(p=>{p.node.style.left=(p.x-p.w/2+shift)+'px';p.node.style.top=(p.y-p.h/2-low+margin)+'px';});
    }
}
// Circle area is proportional to the actual word count.
function renderCircleMap(items, maximum) {
    const host = $('aura-view');
    host.replaceChildren();
    const width = Math.max(1, host.clientWidth || 320);
    const gap = 7;
    const padding = 12;
    const base = Math.min((width-2*padding)*.43, 210, Math.max(65,width/Math.sqrt(items.length)*.72));
    const placed = [];
    items.forEach((item,i)=>{
        const r = base/2 * Math.sqrt(item.count/maximum);
        let point = null;
        // Prefer compact circular packing around the largest word.
        for(let k=0;k<12000;k++){
            const distance=3.5*Math.sqrt(k);
            const angle=k*2.3999632297;
            const x=width/2+Math.cos(angle)*distance*1.5;
            const y=Math.sin(angle)*distance;
            if(x-r<padding||x+r>width-padding)continue;
            if(placed.every(p=>Math.hypot(p.x-x,p.y-y)>=p.r+r+gap)){
                point={x,y,r};break;
            }
        }
        if(!point)point={x:width/2,y:Math.max(0,...placed.map(p=>p.y+p.r))+r+gap,r};
        const node=document.createElement('div');
        node.className='frequency-bubble';
        node.style.width=node.style.height=2*r+'px';
        node.style.setProperty('--ink',colors[i%colors.length]);
        node.style.setProperty('--delay',`${-i*.83}s`);
        node.title=`${item.word}: ${format(item.count)}`;
        node.setAttribute('aria-label',node.title);
        const label=document.createElement('span');
        label.className='bubble-word';label.textContent=item.word;
        const count=document.createElement('small');count.textContent=format(item.count);
        const font=Math.min(30,r*.43,r*2*.85/Math.max(3,item.word.length)*1.65);
        label.style.fontSize=font+'px';count.style.fontSize=Math.min(14,r*.25)+'px';
        if(r>=22)node.append(label,count);
        else {node.tabIndex=0;}
        host.append(node);point.node=node;placed.push(point);
    });
    const left=Math.min(...placed.map(p=>p.x-p.r));
    const right=Math.max(...placed.map(p=>p.x+p.r));
    const low=Math.min(...placed.map(p=>p.y-p.r));
    const high=Math.max(...placed.map(p=>p.y+p.r));
    const shift=(width-left-right)/2;
    host.style.height=Math.ceil(high-low+2*padding)+'px';
    placed.forEach(p=>{p.node.style.left=(p.x-p.r+shift)+'px';p.node.style.top=(p.y-p.r-low+padding)+'px';});
}
let clusterWidth=0;
const clusterObserver=new ResizeObserver(()=>{
    const width=$('aura-view').clientWidth;
    if(current && width && width!==clusterWidth){clusterWidth=width;layoutClusters(current.words.slice(0,Number($('top-limit').value)));}
});
clusterObserver.observe($('aura-view'));

function filtered(){const query=$('word-search').value.toLowerCase(),sort=$('word-sort').value;return current.words.filter(w=>w.word.toLowerCase().includes(query)).sort((a,b)=>sort==='alpha'?a.word.localeCompare(b.word):sort==='asc'?a.count-b.count||a.word.localeCompare(b.word):b.count-a.count||a.word.localeCompare(b.word));}
function renderTable(){if(!current)return;const rows=filtered(), pages=Math.max(1,Math.ceil(rows.length/25));page=Math.min(page,pages-1);$('frequency-table').replaceChildren();for(const w of rows.slice(page*25,page*25+25)){const tr=document.createElement('tr');const a=document.createElement('button');a.className='term-link';a.textContent=w.word;a.onclick=()=>{$('context-search').value=w.word;$('context-output').closest('details').open=true;showContext(true);};const td=document.createElement('td');td.append(a);tr.append(td);for(const v of [format(w.count),(100*w.count/current.total_words).toFixed(2)+'%']){const cell=document.createElement('td');cell.textContent=v;tr.append(cell);}$('frequency-table').append(tr);} $('page-info').textContent=`${rows.length} matches · ${page+1}/${pages}`;$('prev-page').disabled=page===0;$('next-page').disabled=page+1>=pages;}
for(const id of ['word-search','word-sort'])$(id).addEventListener('input',()=>{page=0;renderTable();});$('prev-page').onclick=()=>{page--;renderTable();};$('next-page').onclick=()=>{page++;renderTable();};$('top-limit').onchange=renderVisual;
function showContext(find) {
    if (!current) return;
    const query = $('context-search').value.trim();
    const normalize = value => current.options.case ? value : value.toLowerCase();
    const rows = current.preview.filter(row =>
        !find || !query || row.processed.some(word => normalize(word) === normalize(query))
    );
    $('context-output').textContent = rows.slice(0, 100).map(row =>
        $('preview-mode').value === 'original' ? row.original : row.processed.join(' · ')
    ).join('\n') || 'No matches in the preview.';
}
$('context-find').onclick=()=>showContext(true);$('preview-mode').onchange=()=>showContext(true);
function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function csvText(){return 'Word or phrase,Count\n'+filtered().map(w=>'"'+w.word.replace(/"/g,'""')+'",'+w.count).join('\n');}
$('csv-export').onclick=()=>download('wordly-frequency.csv',csvText(),'text/csv');$('json-export').onclick=()=>{const {preview,comparison,...data}=current;download('wordly-results.json',JSON.stringify(data,null,2),'application/json');};$('copy-export').onclick=async()=>{try{await navigator.clipboard.writeText(csvText());$('copy-export').textContent='Copied';}catch(e){$('copy-export').textContent='Copy failed';}};
$('png-export').onclick=()=>{const original=$('result-spectrum').querySelector('svg');if(!original)return;const svg=original.cloneNode(true);svg.setAttribute('xmlns','http://www.w3.org/2000/svg');const nodes=svg.querySelectorAll('*'), originals=original.querySelectorAll('*');nodes.forEach((n,i)=>{const style=getComputedStyle(originals[i]);for(const key of ['fill','stroke','stroke-width','font-size','font-family','opacity','stroke-dasharray']){const v=style.getPropertyValue(key);if(v&&!v.includes('url('))n.style.setProperty(key,key==='opacity'&&n.classList.contains('frequency-node')?'1':key==='opacity'&&n.classList.contains('frequency-area')?'.045':v);}n.style.animation='none';});svg.querySelectorAll('animateMotion,.light-particle').forEach(n=>n.remove());svg.querySelectorAll('.frequency-line').forEach(n=>n.style.strokeDashoffset='0');const vb=original.viewBox.baseVal;svg.setAttribute('width',vb.width);svg.setAttribute('height',vb.height);const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml'}));const img=new Image();img.onload=()=>{const c=document.createElement('canvas');c.width=vb.width*2;c.height=vb.height*2;const ctx=c.getContext('2d');ctx.fillStyle='#101014';ctx.fillRect(0,0,c.width,c.height);ctx.drawImage(img,0,0,c.width,c.height);c.toBlob(b=>{if(b)download('wordly-graph.png',b,'image/png');});URL.revokeObjectURL(url);};img.onerror=()=>{$('status').textContent='PNG export failed.';URL.revokeObjectURL(url);};img.src=url;};
function renderComparison(){const host=$('comparison');host.replaceChildren();if(current.comparison.length<2)return;const h=document.createElement('h3');h.textContent='Compare files';host.append(h);for(const doc of current.comparison){const title=document.createElement('p');title.textContent=doc.name+' · '+format(doc.total)+' counted';host.append(title);for(const w of current.words.slice(0,10)){const n=Object.prototype.hasOwnProperty.call(doc.counts,w.word)?doc.counts[w.word]:0;const share=doc.total?n/doc.total*100:0;host.append(bar(w.word,share,100,share.toFixed(2)+'%'));}}}
function historyRows(){try{return JSON.parse(localStorage.getItem('wordly-history')||'[]');}catch{return [];}}
function showHistory(){ $('history').replaceChildren();for(const d of historyRows()){const p=document.createElement('p');p.textContent=`${d.date} · ${format(d.lines)} lines · ${d.speedup.toFixed(3)}× speedup`; $('history').append(p);}}
function recordHistory(d){try{localStorage.setItem('wordly-history',JSON.stringify([{date:new Date().toLocaleString(),lines:d.responses,speedup:d.speedup},...historyRows()].slice(0,20)));}catch{}showHistory();}
$('clear-history').onclick=()=>{try{localStorage.removeItem('wordly-history');}catch{}showHistory();};showHistory();
const dropArea=document.querySelector('.upload');
for(const event of ['dragenter','dragover'])dropArea.addEventListener(event,e=>{e.preventDefault();dropArea.classList.add('dragging');});
for(const event of ['dragleave','drop'])dropArea.addEventListener(event,e=>{e.preventDefault();dropArea.classList.remove('dragging');});
dropArea.addEventListener('drop',e=>{if(e.dataTransfer.files.length){$('file').files=e.dataTransfer.files;$('file').dispatchEvent(new Event('change'));}});

const backTop = $('back-to-top');
function updateBackTop(){backTop.hidden=window.scrollY<300;}
window.addEventListener('scroll',updateBackTop,{passive:true});
backTop.addEventListener('click',()=>window.scrollTo({top:0,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}));
updateBackTop();
