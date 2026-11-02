"""Check the saved demonstration's actual mesh, solver and field outputs."""
from pathlib import Path
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile

root = Path(__file__).resolve().parent.parent
mesh_log = (root / 'mesh-check.log').read_text(encoding='utf-8')
solver_log = (root / 'solver-run.log').read_text(encoding='utf-8')
assert 'Mesh OK.' in mesh_log, 'Mesh quality did not pass'
assert not re.search(
    r'FOAM FATAL|^\s*(?:Floating point exception|Segmentation fault)(?:\s*\(core dumped\))?\s*$',
    solver_log, re.I | re.M,
), 'Solver fatal error detected'
cells = int(re.search(r'^\s*cells:\s*(\d+)', mesh_log, re.M).group(1))
iteration = int(re.findall(r'SIMPLE solution converged in (\d+) iterations', solver_log)[-1])
assert solver_log.rstrip().endswith('End'), 'Solver did not end normally'

field_report = {}
for name, components in [('U', 3), ('p', 1)]:
    text = (root / 'case' / str(iteration) / name).read_text(encoding='utf-8')
    field = re.search(r'internalField\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\)\s*;', text, re.S)
    assert field is not None, f'{name}: missing field data'
    count = int(field.group(1))
    values = [float(v) for v in re.findall(r'[-+]?(?:\d*\.?\d+(?:[Ee][-+]?\d+)?|nan|inf)', field.group(2), re.I)]
    assert count == cells and len(values) == count * components, f'{name}: unexpected field size'
    assert all(math.isfinite(v) for v in values), f'{name}: non-finite values'
    field_report[name] = {'cells': count, 'components': components, 'all_values_finite': True}

with zipfile.ZipFile(root / 'Elbow-CFD.FCStd') as archive:
    assert archive.testzip() is None, 'FreeCAD document CRC failure'
    ET.fromstring(archive.read('Document.xml'))

summary = json.loads((root / 'result-summary.json').read_text(encoding='utf-8'))
assert summary['cells'] == cells and summary['iteration'] == iteration
for filename in ['velocity.png', 'pressure.png', 'freecad-mesh.png']:
    assert (root / filename).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')

report = {
    'status': 'pass', 'cells': cells, 'converged_iteration': iteration,
    'mesh_quality': 'Mesh OK', 'fields': field_report,
    'freecad_document_crc_and_xml': 'pass',
    'scope': 'Integration smoke test; physical accuracy and mesh independence are not validated',
}
(root / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
