from pathlib import Path
import json, math, re

root=Path(__file__).resolve().parent.parent
reports={}
for key in ['a','b']:
    folder=root/('case-'+key)
    setup=json.loads((folder/'setup.json').read_text())
    meshlog=(folder/'mesh-check.log').read_text()
    log=(folder/'solver-run.log').read_text()
    assert 'Mesh OK.' in meshlog, f'{key}: mesh quality not passed'
    cells=int(re.search(r'^\s*cells:\s*(\d+)',meshlog,re.M).group(1))
    converged=re.findall(r'SIMPLE solution converged in (\d+) iterations',log)
    assert converged, f'{key}: SIMPLE convergence not reached'
    iteration=int(converged[-1])
    assert log.rstrip().endswith('End'), f'{key}: solver did not end normally'
    assert not re.search(r'FOAM FATAL|^\s*(?:Floating point exception|Segmentation fault)(?:\s*\(core dumped\))?\s*$',log,re.I|re.M)
    fields={}
    for name,components in [('U',3),('p',1),('k',1),('epsilon',1)]:
        content=(folder/'case'/str(iteration)/name).read_text()
        field=re.search(r'internalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\)\s*;',content,re.S)
        assert field, f'{key}: {name} absent/nonuniform field missing'
        values=[float(s) for s in re.findall(r'[-+]?(?:\d*\.?\d+(?:[Ee][-+]?\d+)?|nan|inf)',field.group(2),re.I)]
        assert int(field.group(1))==cells and len(values)==cells*components
        assert all(math.isfinite(v) for v in values)
        if name in ['k','epsilon']: assert min(values)>=0
        fields[name]={'cells':cells,'components':components,'finite':True,'minimum_component':min(values),'maximum_component':max(values)}
    final_block=log.split(f'Time = {iteration}\n')[-1]
    residuals={}
    for name in ['Ux','Uy','p','k','epsilon']:
        match=re.search(r'Solving for '+name+r', Initial residual = ([^,]+)',final_block)
        assert match, f'{key}: missing residual for {name}'
        residuals[name]=float(match.group(1))
        assert residuals[name]<=setup['convergence_tolerance'], f'{key}: residual {name} above target'
    reports[key]={'status':'pass','cells':cells,'converged_iteration':iteration,'initial_residuals_at_final_iteration':residuals,'tolerance':setup['convergence_tolerance'],'fields':fields,'model':setup['turbulence'],'mesh_quality':'Mesh OK'}
    (folder/'validation.json').write_text(json.dumps(reports[key],indent=2),encoding='utf-8')
(root/'solver-validation.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports))
