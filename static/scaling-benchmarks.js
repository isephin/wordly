(() => {
  const select = document.getElementById('scaling-workers');
  const graph = document.getElementById('scaling-graph');
  const table = document.getElementById('scaling-table');
  const note = document.getElementById('scaling-note');
  const groups = new Map();
  function render() {
    graph.replaceChildren(); table.replaceChildren();
    const choice = select.value;
    note.textContent = 'Average time per run. Shorter bars are faster. Each dataset has its own scale. Efficiency = speedup ÷ workers × 100%.';
    for (const [size, rows] of [...groups].sort((a,b)=>a[0]-b[0])) {
      const seq = rows.find(r=>r.workers===1);
      const candidates = rows.filter(r=>r.workers>1).sort((a,b)=>a.mean_seconds-b.mean_seconds || a.workers-b.workers);
      const par = choice==='best'?candidates[0]:candidates.find(r=>r.workers===Number(choice));
      if (!seq || !par) continue;
      const tr = document.createElement('tr');
      for (const value of [size.toLocaleString(),par.workers,seq.mean_seconds.toFixed(6)+' s',par.mean_seconds.toFixed(6)+' s',par.speedup.toFixed(3)+'×',par.local_efficiency_percent.toFixed(2)+'%']) {
        const td=document.createElement('td');td.textContent=value;tr.append(td);
      }
      table.append(tr);
      const group=document.createElement('div');group.style.marginBottom='25px';
      const label=document.createElement('p');label.textContent=`${size.toLocaleString()} responses · ${par.workers} workers · ${seq.mean_seconds<=par.mean_seconds?'Sequential':'Parallel'} faster`;
      const max=Math.max(seq.mean_seconds,par.mean_seconds);
      group.append(label,bar('Sequential',seq.mean_seconds,max,seq.mean_seconds.toFixed(6)+' s'),bar('Parallel',par.mean_seconds,max,par.mean_seconds.toFixed(6)+' s','linear-gradient(90deg,#3d7895,#b6dbb0)'));
      graph.append(group);
    }
  }
  async function load(){
    try{
      const response=await fetch('/api/benchmarks/scaling');
      if(!response.ok) throw Error('request failed');
      const data=await response.json();
      if(!Array.isArray(data)||!data.length){note.textContent='No scaling results available. See the original benchmark below.';return;}
      const counts=new Set();
      for(const raw of data){
        const r={...raw};for(const key of ['lines','workers','mean_seconds','speedup','local_efficiency_percent'])r[key]=Number(r[key]);
        if(!Number.isInteger(r.lines)||r.lines<1||!Number.isInteger(r.workers)||r.workers<1||!Number.isFinite(r.mean_seconds)||r.mean_seconds<=0||!Number.isFinite(r.speedup)||!Number.isFinite(r.local_efficiency_percent))throw Error('invalid data');
        if(!groups.has(r.lines))groups.set(r.lines,[]);groups.get(r.lines).push(r);if(r.workers>1)counts.add(r.workers);
      }
      for(const n of [...counts].sort((a,b)=>a-b)){const option=document.createElement('option');option.value=String(n);option.textContent=n+' workers';select.append(option);}
      select.disabled=false;select.addEventListener('change',render);render();
    }catch(e){note.textContent='Could not load results. See the original benchmark below.';}
  }
  load();
})();
