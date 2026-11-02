from pathlib import Path
import re,json
here=Path(__file__).resolve().parent
out=here.parent if (here.parent/'setup.json').exists() else here.parents[1]/'experiments/family-house-airflow'
allrun=out/'case/Allrun'
txt=allrun.read_text()
txt=txt.replace('    runCommand simpleFoam','    runCommand decomposePar -force\n    runParallel 8 simpleFoam\n    runCommand reconstructPar -latestTime')
allrun.write_text(txt,newline='\n')
p=out/'case/system/decomposeParDict';p.write_text(p.read_text().replace('numberOfSubdomains  4;','numberOfSubdomains  8;'),newline='\n')
p=out/'case/system/controlDict';p.write_text(p.read_text().replace('purgeWrite      0;','purgeWrite      2;'),newline='\n')
s=json.loads((out/'setup.json').read_text(encoding='utf-8'))
s['numerics']={'velocity_advection':'bounded Gauss upwind (first-order)','relaxation_U':.4,'relaxation_p':.15,'relaxation_turbulence':.4,'solver_processes':8,'convergence_tolerance':1e-4,'max_iterations':6000}
s['geometry_assets']={'building-shell.stl':'building walls/floors/ceiling/native hip roof AND awning flaps, excludes furniture','obstacles.stl':'entire building-shell plus included furniture'}
(out/'setup.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('Parallel and purge prepared')
