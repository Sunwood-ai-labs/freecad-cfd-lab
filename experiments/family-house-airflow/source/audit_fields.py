"""Independent finite-field, units, count, residual and hash audit."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--case',required=True,type=Path);p.add_argument('--time',required=True);p.add_argument('--log',required=True,type=Path);p.add_argument('--tol',required=True,type=float);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
fields={}
cell_count=None
expected_dimensions={'U':[0,1,-1,0,0,0,0],'p':[0,2,-2,0,0,0,0],'k':[0,2,-2,0,0,0,0],'epsilon':[0,2,-3,0,0,0,0],'nut':[0,2,-1,0,0,0,0],'C':[0,1,0,0,0,0,0]}
for name,components in [('U',3),('p',1),('k',1),('epsilon',1),('nut',1),('C',3)]:
    path=a.case/a.time/name
    raw=path.read_bytes();text=raw.decode('utf-8')
    dimensions=[int(v) for v in re.search(r'\bdimensions\s*\[([^]]+)\]',text)[1].split()]
    assert dimensions==expected_dimensions[name],(name,dimensions)
    header=re.search(r'\binternalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\(',text)
    assert header,(name,'No nonuniform field')
    end=re.search(r'^\s*\)\s*;',text[header.end():],re.M)
    assert end
    values=np.fromstring(text[header.end():header.end()+end.start()].replace('(',' ').replace(')',' '),sep=' ')
    count=int(header[1]);assert len(values)==count*components
    assert np.isfinite(values).all(),name
    if cell_count is None:cell_count=count
    assert count==cell_count,(name,count,cell_count)
    if name in ['k','epsilon','nut']:assert values.min()>=0
    fields[name]={'cells':count,'components':components,'finite':True,'dimensions':dimensions,'min_component':float(values.min()),'max_component':float(values.max()),'sha256':hashlib.sha256(raw).hexdigest()}
    if name=='U':fields[name]['maximum_speed_m_s']=float(np.linalg.norm(values.reshape(-1,3),axis=1).max())
log=a.log.read_text(encoding='utf-8')
blocks=re.split(r'\nTime = ',log)
block=next(b for b in reversed(blocks) if b.startswith(a.time+'\n') and all('Solving for '+name+',' in b for name in ['Ux','Uy','Uz','p','k','epsilon']))
initial={}
for name,res in re.findall(r'Solving for (\w+), Initial residual = ([^,]+)',block):
    initial.setdefault(name,float(res))
assert set(['Ux','Uy','Uz','p','k','epsilon']).issubset(initial)
assert all(r<=a.tol for r in initial.values()),initial
assert re.search(r'SIMPLE solution converged in '+re.escape(a.time)+r' iterations',log)
assert 'FOAM FATAL' not in block
result={'status':'pass','source_case':str(a.case.resolve()),'source_time':a.time,'cells':cell_count,'fields':fields,'initial_residuals':initial,'residual_tolerance':a.tol,'scope':'Finite fields, correct counts, turbulence nonnegativity and residual gate; not a statement of physics accuracy or iterative observable stability'}
a.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'cells':cell_count,'time':a.time,'residuals':initial,'U_sha256':fields['U']['sha256']},indent=2))
