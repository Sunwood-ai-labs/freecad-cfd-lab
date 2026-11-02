from pathlib import Path
import re,json
here=Path(__file__).resolve().parent
out=here.parent if (here.parent/'setup.json').exists() else here.parents[1]/'experiments/family-house-airflow'
log=(out/'solver-run.log').read_text(encoding='utf-8');rows=[]
for b in re.split(r'\nTime = ',log)[1:]:
    step=int(b.split()[0]);row={'iteration':step}
    for m in re.finditer(r'Solving for (\w+), Initial residual = ([\deE+.\-]+)',b):row.setdefault(m.group(1),float(m.group(2)))
    if 'k' in row:rows.append(row)
(out/'residual-history.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for start in range(0,len(rows),100):
    part=rows[start:start+100]
    print(part[0]['iteration'],part[-1]['iteration'],{f:(min(x[f] for x in part),max(x[f] for x in part),part[-1][f]) for f in ['Ux','p','k']})
