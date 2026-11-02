from pathlib import Path
import json,zipfile,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent.parent
results={}
for key in ['a','b']:
    file=root/('case-'+key)/('House-'+key.upper()+'.FCStd')
    with zipfile.ZipFile(file) as z:
        assert z.testzip() is None
        xml=z.read('Document.xml').decode('utf-8')
        tree=ET.fromstring(xml)
        assert 'kEpsilon' in xml and 'bounded Gauss upwind' in xml
        assert 'planar2D' in xml
        # The saved model itself must contain the final solver controls.
        for name in ['URelaxation','pRelaxation','TurbulenceRelaxation','VelocityAdvectionOverride']:
            assert tree.findall(f'.//Property[@name="{name}"]'),name
    results[key]={'path':str(file),'bytes':file.stat().st_size,'zip_crc':'pass','xml':'pass','contains_final_physics_and_override':True}
(root/'saved-model-validation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results))
