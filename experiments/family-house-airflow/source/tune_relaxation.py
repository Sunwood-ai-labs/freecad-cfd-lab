from pathlib import Path
import json,re,time
here=Path(__file__).resolve().parent
out=here.parent if (here.parent/'setup.json').exists() else here.parents[1]/'experiments/family-house-airflow'
while True:
    steps=re.findall(r'\nTime = (\d+)\s*\n',(out/'solver-run.log').read_text(encoding='utf-8'))
    if steps and int(steps[-1])>=100:break
    time.sleep(3)
p=out/'case/system/fvSolution';txt=p.read_text()
for field,value in [('U',.6),('k',.6),('epsilon',.6),('p',.3)]:
    txt=re.sub(r'(?m)^(\s*'+field+r'\s+)[.\d]+;',lambda m:m.group(1)+str(value)+';',txt)
p.write_text(txt,newline='\n')
p=out/'setup.json';s=json.loads(p.read_text(encoding='utf-8'))
s['numerics'].update(relaxation_U=.6,relaxation_p=.3,relaxation_turbulence=.6)
s['numerics']['relaxation_history']=[{'iteration_start':0,'U':.4,'p':.15,'turbulence':.4},{'iteration_start':int(steps[-1]),'U':.6,'p':.3,'turbulence':.6}]
s['mesh_target'].update(fcl_room_m=.0625,wardrobe_top_gap_m=.03125,thin_tabletops_m=.03125,washer_side_gap_m=.03125,wc_50mm_rear_gap_m=.015625)
p.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('Raised relaxation at iteration '+steps[-1])
