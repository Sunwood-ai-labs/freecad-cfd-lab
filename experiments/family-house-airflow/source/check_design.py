import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
plan = json.loads((ROOT / 'experiments/family-house/house-design.json').read_text(encoding='utf-8'))
windows = []
for o in plan['openings']:
    if o['kind'] != 'window':
        continue
    frame = o['frame_width']
    clear_width = (o['width'] - 2 * frame) / (2 if o['operation'] == 'sliding' else 1)
    clear_height = o['height'] - 2 * frame
    windows.append({
        'id': o['id'], 'room': next(r for r in o['connects'] if r != 'outside'),
        'host': o['host'], 'center_mm': o['center'], 'axis': o['axis'], 'original_operation': o['operation'],
        'open_width_mm': clear_width, 'open_height_mm': clear_height,
        'open_area_m2': clear_width * clear_height / 1e6,
        'bottom_gl_mm': 450 + o['sill'] + frame,
        'top_gl_mm': 450 + o['sill'] + o['height'] - frame,
        'assumption': ('One half of frame-inner width unobstructed; other half closed; product not selected' if o['operation'] == 'sliding' else 'Top-hung awning frame-inner hole with physical outward 45degree leaf preferred; any equivalent unobstructed surrogate must be declared'),
        'area_note': 'Geometric wall throat area; awning flap additionally restricts discharge and this is NOT rated ventilation effective area',
    })

inside = {r['id'] for r in plan['rooms']}
graph = {r: set() for r in inside}
for o in plan['openings']:
    if o['kind'] == 'window' or o['id'] == 'D01':
        continue
    a, b = o['connects']
    graph[a].add(b)
    graph[b].add(a)
reachable = {'ldk'}
while True:
    after = reachable | set().union(*(graph[r] for r in reachable))
    if after == reachable:
        break
    reachable = after
report = {
    'source_revision': plan['design_revision'],
    'window_assumption': 'W01-07 two-panel sliding: aperture width=(rough width-100)/2, height=rough height-100. W08-09 are top-hung awning, preserve operation and physical flap or declare surrogate. No insect screens.',
    'window_openings': windows,
    'sum_open_area_m2': sum(w['open_area_m2'] for w in windows),
    'room_connection_graph': {k: sorted(v) for k, v in graph.items()},
    'all_rooms_connected_in_open_door_graph': reachable == inside,
    'rooms_without_external_windows': sorted(inside - {w['room'] for w in windows}),
    'geometry_gates': [
        'House exterior 12.1 x 9.1 m, partitions and room boundaries match R4',
        'Interior floor GL450 except entry GL300; ceiling sealed at GL2850',
        'Foundation/floor prevent external flow under floor entering interior',
        'Roof volume is external obstacle; attic sealed from occupied rooms',
        'Entrance D01 shut; all other internal doors open; leaves absent/simplified must be disclosed',
        'Every opening cut survives mesh, narrowest sliding W03 width0.4m; awning flap projected clearance must have several cells across',
        'Furniture solid simplification listed; wet_floor reference marker must NOT be obstacle',
    ],
    'numerical_gates': [
        'checkMesh succeeds, no negative volume / invalid topology, connected interior/exterior region',
        'Final U,p,k,epsilon are finite; k,epsilon nonnegative',
        'Residual gate e.g. all initial residuals<1e-4 explicitly recorded',
        'Exterior flux closure and continuity residual recorded, not inferred from process exit',
        'Each room boundary flux imbalance relative to inlet checked separately, target below1% for flowing rooms; report absolute for tiny flows',
        'Window and door signed inlet/outlet volumes measured from conservative face flux phi where possible',
        'Stable window flows over late iterations or explicit unconverged limitation',
        'No claim of grid independence without independent refinement test',
    ],
    'visualization_gates': [
        'Actual 3D field, common physical IntegrationTime multiplier, no fabricated room paths',
        'If projecting streamlines, show that height is collapsed and avoid implying floor-level velocity',
        'High windows W08/W09 are not represented by a single floor-height slice',
        'Particles are flow-direction tracers, not air exchange efficiency or transient gusts',
        'If only one wind direction, do not rank design generally',
        'No external window rooms are one-mouth cavities: mean speed is not fresh-air ventilation metric',
    ],
    'official_sources': [
        'https://doc.openfoam.com/2306/tools/processing/solvers/rtm/incompressible/simpleFoam/',
        'https://doc.openfoam.com/2306/tools/processing/numerics/solvers/case-termination/',
        'https://vtk.org/doc/release/7.1/html/classvtkStreamTracer.html',
        'https://github.com/Kitware/VTK/blob/master/Filters/FlowPaths/vtkStreamTracer.cxx',
    ],
}
out = Path(__file__).with_name('design-audit.json')
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'output': str(out), 'windows': windows, 'open_area_m2': report['sum_open_area_m2'], 'room_graph_pass': reachable == inside}, ensure_ascii=True, indent=2))
