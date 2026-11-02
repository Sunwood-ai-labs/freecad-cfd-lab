from pathlib import Path
import json
here=Path(__file__).resolve().parent
out=here.parent if (here.parent/'setup.json').exists() else here.parents[1]/'experiments/family-house-airflow'
p=out/'case/system/fvSolution'
p.write_text(p.read_text().replace('nNonOrthogonalCorrectors 5;','nNonOrthogonalCorrectors 1;'),newline='\n')
p=out/'case/system/fvSchemes'
p.write_text(p.read_text().replace('// Use second-order accurate convection','// First-order upwind convection used for this case'),newline='\n')
p=out/'setup.json';s=json.loads(p.read_text(encoding='utf-8'))
s['numerics']['non_orthogonal_correctors']=1
s['numerics']['tuning_note']='Accepted 538479-cell run uses 1 non-orthogonal correction from its start; mesh max nonorth64.8deg, no porous baffle. Earlier discarded coarse run began with template default 5. Final conservation gates remain unchanged.'
p.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('Set one nonorthogonal correction')
