from pathlib import Path
import json,re,math,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent
OUT=HERE.parent if (HERE.parent/'setup.json').exists() else HERE.parents[1]/'experiments/family-house-airflow'
CASE=OUT/'case'

def internal_array(path,components=1):
    txt=path.read_text(encoding='utf-8')
    m=re.search(r'internalField\s+nonuniform\s+\S+\s+(\d+)\s*\((.*?)\)\s*;',txt,re.S)
    if not m: raise ValueError('Missing nonuniform internal array: '+str(path))
    a=np.fromstring(m.group(2).replace('(',' ').replace(')',' '),sep=' ')
    n=int(m.group(1));assert len(a)==n*components,(path,n,len(a))
    return a.reshape((-1,components)) if components>1 else a
def label_array(path):
    txt=path.read_text(encoding='utf-8');m=re.search(r'\n(\d+)\s*\n\((.*?)\)\s*',txt,re.S)
    if not m: raise ValueError(str(path))
    a=np.fromstring(m.group(2),dtype=np.int64,sep=' ');assert len(a)==int(m.group(1));return a

times=sorted([p for p in CASE.iterdir() if p.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?',p.name)],key=lambda p:float(p.name))
latest=times[-1]; n=0;fields={}
for field,c in [('U',3),('p',1),('k',1),('epsilon',1),('nut',1)]:
    a=internal_array(latest/field,c);n=len(a)
    fields[field]={'cells':n,'components':c,'finite':bool(np.isfinite(a).all()),'minimum_component':float(a.min()),'maximum_component':float(a.max())}
    if field=='U': fields[field]['max_speed_m_s']=float(np.linalg.norm(a,axis=1).max())
    assert fields[field]['finite']
    if field in ['k','epsilon','nut']: assert a.min()>=0
log=(OUT/'solver-run.log').read_text(encoding='utf-8')
converged=re.findall(r'SIMPLE solution converged in (\d+) iterations',log)
lastblock=next(b for b in reversed(re.split(r'\nTime = ',log)) if 'Solving for Ux' in b)
residuals={}
for m in re.finditer(r'Solving for (\w+), Initial residual = ([\deE+.\-]+)',lastblock):
    residuals.setdefault(m.group(1),float(m.group(2)))
assert converged,'No residual-based convergence'
assert all(v<=1e-4 for v in residuals.values()),residuals
mesh=(OUT/'mesh-check.log').read_text(encoding='utf-8');assert 'Mesh OK.' in mesh
phi=internal_array(latest/'phi');owner=label_array(CASE/'constant/polyMesh/owner');neighbor=label_array(CASE/'constant/polyMesh/neighbour')
assert len(phi)==len(neighbor)
ptxt=(latest/'phi').read_text(); btxt=(CASE/'constant/polyMesh/boundary').read_text()
patches=[]
for m in re.finditer(r'(\w+)\s*\{[^{}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);[^{}]*\}',btxt,re.S):
    name,nfaces,start=m.group(1),int(m.group(2)),int(m.group(3));pm=re.search(r'\b'+re.escape(name)+r'\s*\{(.*?)\n\s*\}',ptxt,re.S)
    assert pm,(name,'phi missing')
    block=pm.group(1);vals=re.search(r'value\s+nonuniform\s+\S+\s+(\d+)\s*\((.*?)\)\s*;',block,re.S)
    if vals: a=np.fromstring(vals.group(2),sep=' ');assert len(a)==nfaces
    else:
        v=re.search(r'value\s+uniform\s+([\deE+.\-]+);',block);a=np.full(nfaces,float(v.group(1))) if v else np.zeros(nfaces)
    patches.append({'name':name,'start':start,'nfaces':nfaces,'array':a})
div=np.bincount(owner[:len(phi)],weights=phi,minlength=n)-np.bincount(neighbor,weights=phi,minlength=n)
for p in patches: div+=np.bincount(owner[p['start']:p['start']+p['nfaces']],weights=p['array'],minlength=n)
patch_summary={p['name']:{'net_outflow_m3_s':float(p['array'].sum()),'inflow_m3_s':float(-p['array'][p['array']<0].sum()),'outflow_m3_s':float(p['array'][p['array']>0].sum())} for p in patches}
inflow=sum(v['inflow_m3_s'] for v in patch_summary.values());net=sum(v['net_outflow_m3_s'] for v in patch_summary.values())
global_rel=abs(net)/inflow
C=internal_array(latest/'C',3);assert len(C)==n
setup=json.loads((OUT/'setup.json').read_text(encoding='utf-8'));rooms={}
for r in setup['rooms']:
    bb=r['bbox_m'];mask=np.all((C>=np.array(bb[:3]))&(C<=np.array(bb[3:])),axis=1)
    own=mask[owner[:len(phi)]];nei=mask[neighbor];cross=own!=nei
    outward=phi[cross]*np.where(own[cross],1,-1)
    for p in patches:
        am=mask[owner[p['start']:p['start']+p['nfaces']]]
        outward=np.concatenate([outward,p['array'][am]])
    qi=float(-outward[outward<0].sum());qo=float(outward[outward>0].sum());qnet=float(outward.sum())
    rooms[r['id']]={'name':r['name'],'selection':'cell centres inside clear-room bbox; conservative phi across selected cell-set boundary',
        'cells':int(mask.sum()),'inflow_m3_s':qi,'outflow_m3_s':qo,'net_outflow_m3_s':qnet,'relative_mass_imbalance':abs(qnet)/max(qi,1e-12),'sum_cell_divergence_m3_s':float(div[mask].sum())}
result={'status':'pass' if global_rel<.001 and all(r['relative_mass_imbalance']<.01 for r in rooms.values()) else 'needs_review',
    'cells':n,'final_time':latest.name,'converged_iteration':int(converged[-1]),'initial_residuals_at_final_iteration':residuals,
    'fields':fields,'mesh_quality':'Mesh OK','global_mass_balance':{'inflow_m3_s':inflow,'net_outflow_m3_s':net,'relative_imbalance':global_rel},
    'boundary_fluxes':patch_summary,'room_cellset_mass_balances':rooms,'max_absolute_cell_flux_divergence_m3_s':float(np.abs(div).max()),
    'caveat':'Cell-set boundary mass fluxes are numerical conservation diagnostics, not exact architectural door/window opening flow or fresh-air delivery.'}
(OUT/'solver-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
