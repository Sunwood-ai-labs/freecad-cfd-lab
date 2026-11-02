from pathlib import Path
import re,json
here=Path(__file__).resolve().parent
out=here.parent if (here.parent/'setup.json').exists() else here.parents[1]/'experiments/family-house-airflow'
p=out/'case/system/fvSolution';txt=p.read_text()
for field,value in [('U',.4),('k',.4),('epsilon',.4),('p',.15)]:
    txt=re.sub(r'(?m)^(\s*'+field+r'\s+)[.\d]+;',lambda m:m.group(1)+str(value)+';',txt)
p.write_text(txt,newline='\n')
p=out/'setup.json';s=json.loads(p.read_text(encoding='utf-8'))
s['numerics'].update(relaxation_U=.4,relaxation_p=.15,relaxation_turbulence=.4)
s['numerics']['relaxation_history']=[{'iteration_start':0,'U':.4,'p':.15,'turbulence':.4}]
p.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('Reset initial relaxation; run tune_relaxation.py alongside solver for change after iteration 100')
