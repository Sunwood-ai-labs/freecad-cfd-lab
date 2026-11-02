from pathlib import Path
import re,json
here=Path(__file__).resolve().parent
out=here.parent if (here.parent/'setup.json').exists() else here.parents[1]/'experiments/family-house-airflow'
p=out/'case/system/controlDict';txt=p.read_text()
txt=re.sub(r'writeInterval\s+\d+;','writeInterval   100;',txt)
txt=re.sub(r'purgeWrite\s+\d+;','purgeWrite      3;',txt)
p.write_text(txt,newline='\n')
p=out/'setup.json';s=json.loads(p.read_text(encoding='utf-8'));s['numerics'].update(write_interval=100,purge_write=3)
p.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('Capture each 100 iterations; retain last 3 for stability check')
