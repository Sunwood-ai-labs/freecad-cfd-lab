import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
source = ROOT / 'experiments/family-house/house-design.json'
model = ROOT / 'experiments/family-house/4人家族の平屋_BIM.FCStd'
plan = json.loads(source.read_text(encoding='utf-8'))
setup = json.loads((ROOT / 'experiments/family-house-airflow/setup.json').read_text(encoding='utf-8'))
expected_hash = 'd71f486357cc4d18e620b51b2ea9c53f6f65255f4bc50565f70297c2f8e89662'
expected_model_hash = 'e3684f153d9b4e368f4e999cf78f46bce93eee6412e5e97833cd467241039eb9'
checks = []
def check(name, actual, expected):
    checks.append({'check': name, 'pass': actual == expected, 'actual': actual, 'expected': expected})

check('original_plan_preserved', hashlib.sha256(source.read_bytes()).hexdigest(), expected_hash)
check('original_bim_preserved', hashlib.sha256(model.read_bytes()).hexdigest(), expected_model_hash)
check('solver_source_plan_hash', setup['design_sha256'], expected_hash)
check('revision', setup['design_revision'], 'R4-frozen')
check('wind', setup['wind_m_s'], [0, 2, 0])
check('fluid_single_solid', setup['fluid_solids'], 1)
check('floor_ceiling_closed_flag', setup['sealed_floor_and_ceiling'], True)
check('room_count', len(setup['rooms']), 12)
apertures = {o['id']: o for o in setup['apertures']}
check('entrance_closed_no_aperture', 'D01' not in apertures, True)
for room in plan['rooms']:
    actual = next(r for r in setup['rooms'] if r['id'] == room['id'])
    check(room['id'] + ': bbox', actual['bbox'], room['bbox'])
    check(room['id'] + ': floor', actual['floor_level'], room['floor_level'])
    check(room['id'] + ': ceiling', actual['ceiling_level'], room['ceiling_level'])
for source_op in plan['openings']:
    if source_op['id'] == 'D01':
        continue
    a = apertures[source_op['id']]
    check(a['id'] + ': operation', a['original_operation'], source_op['operation'])
    check(a['id'] + ': connectivity', a['connects'], source_op['connects'])
    if source_op['kind'] == 'window':
        width = (source_op['width'] - 2 * source_op['frame_width']) / (2 if source_op['operation'] == 'sliding' else 1) / 1000
        height = (source_op['height'] - 2 * source_op['frame_width']) / 1000
        bottom = (450 + source_op['sill'] + source_op['frame_width']) / 1000
        check(a['id'] + ': width', a['clear_width_m'], width)
        check(a['id'] + ': height', a['clear_height_m'], height)
        check(a['id'] + ': sill_gl', a['aperture_bbox_m'][2], bottom)
        if source_op['operation'] == 'awning':
            check(a['id'] + ': flap45', a.get('flap_angle_degrees'), 45)
            check(a['id'] + ': original_not_surrogate', a['surrogate'], False)

result = {'status': 'pass' if all(c['pass'] for c in checks) else 'fail',
          'checked_against': str(source), 'checks': checks,
          'scope': 'Independent setup-to-design check; flags do not independently prove meshed topology or solved velocity field',
          'window_throat_area_m2': sum(o['area_m2'] for o in setup['apertures'] if o['kind'] == 'window')}
out = Path(__file__).with_name('setup-audit.json')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'checks': len(checks), 'failed': [c for c in checks if not c['pass']], 'window_throat_area_m2': result['window_throat_area_m2']}, ensure_ascii=True, indent=2))
