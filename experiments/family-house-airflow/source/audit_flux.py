"""Independent conservative phi audit. Run through uv --with numpy.

Reads existing ASCII OpenFOAM mesh/fields only. Room sets use cell centres;
their jagged cell-face boundary is conservative, not a geometric opening integral.
"""
import argparse
import gzip
import json
import hashlib
import re
from pathlib import Path

import numpy as np


def read(path):
    if not path.exists() and path.with_suffix(path.suffix + '.gz').exists():
        path = path.with_suffix(path.suffix + '.gz')
    text = gzip.open(path, 'rt').read() if path.suffix == '.gz' else path.read_text()
    if re.search(r'format\s+binary\s*;', text):
        raise ValueError(f'ASCII field required: {path}')
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)


def main_list(text, dtype):
    match = re.search(r'\b(\d+)\s*\(\s*([\s\S]*)\)\s*$', text)
    if match is None:
        raise ValueError('No top-level OpenFOAM list')
    data = np.fromstring(match[2].replace('(', ' ').replace(')', ' '), sep=' ', dtype=dtype)
    if data.size != int(match[1]):
        raise ValueError(f'List count mismatch {data.size} != {match[1]}')
    return data


def field(text, key, n, components=1):
    match = re.search(r'\b' + re.escape(key) + r'\s+(nonuniform\s+List<\w+>\s+\d+\s*\(|uniform\s+)', text)
    if match is None:
        raise ValueError(f'{key}: value missing')
    rest = text[match.end():]
    if 'nonuniform' in match[1]:
        count = int(re.search(r'List<\w+>\s+(\d+)', match[1])[1])
        end = re.search(r'\)\s*;', rest)
        values = np.fromstring(rest[:end.start()].replace('(', ' ').replace(')', ' '), sep=' ')
        assert count == n and values.size == n * components
        return values.reshape((n, components)) if components > 1 else values
    value = np.fromstring(rest.split(';', 1)[0].replace('(', ' ').replace(')', ' '), sep=' ')
    assert value.size == components
    return np.tile(value, (n, 1)) if components > 1 else np.full(n, value.item())


def braces(text):
    """Return immediate named dictionaries, retaining nested contents."""
    result = {}
    i = 0
    while i < len(text):
        match = re.search(r'([\w.\-]+)\s*\{', text[i:])
        if match is None:
            break
        begin = i + match.end()
        depth = 1
        j = begin
        while depth and j < len(text):
            depth += (text[j] == '{') - (text[j] == '}')
            j += 1
        result[match[1]] = text[begin:j - 1]
        i = j
    return result


def flux_report(owner, neighbour, phi, member, all_faces=False):
    n_internal = neighbour.size
    own = member[owner]
    nei = np.zeros(owner.size, dtype=bool)
    nei[:n_internal] = member[neighbour]
    exposed = own != nei
    oriented = np.where(own, phi, -phi)[exposed]
    incoming = float(-oriented[oriented < 0].sum())
    outgoing = float(oriented[oriented > 0].sum())
    net = outgoing - incoming
    return {'boundary_faces': int(exposed.sum()), 'inflow_m3_s': incoming,
            'outflow_m3_s': outgoing, 'net_outflow_m3_s': net,
            'relative_imbalance': abs(net) / max(incoming, outgoing, 1e-12),
            'signed_definition': 'positive is out of cell-centre-defined region'}


parser = argparse.ArgumentParser()
parser.add_argument('--case', required=True, type=Path)
parser.add_argument('--time', required=True)
parser.add_argument('--plan', required=True, type=Path)
parser.add_argument('--offset', type=float, nargs=3, default=(0, 0, 0), help='metres added to original GL coordinates')
parser.add_argument('--out', required=True, type=Path)
parser.add_argument('--global-only', action='store_true')
args = parser.parse_args()
mesh = args.case / 'constant/polyMesh'
owner = main_list(read(mesh / 'owner'), np.int64)
neighbour = main_list(read(mesh / 'neighbour'), np.int64)
ncells = int(max(owner.max(), neighbour.max()) + 1)
phi_text = read(args.case / args.time / 'phi')
assert re.search(r'dimensions\s*\[\s*0\s+3\s+-1\s+0\s+0\s+0\s+0\s*\]',phi_text), 'Expected volumetric flux dimensions m3/s'
phi = np.empty(owner.size)
phi[:neighbour.size] = field(phi_text, 'internalField', neighbour.size)
boundaries = braces(read(mesh / 'boundary').split('FoamFile', 1)[-1])
boundary_start = phi_text.index('boundaryField')
phibc = braces(braces(phi_text[boundary_start:])['boundaryField'])
patch_reports = {}
for name, block in boundaries.items():
    if name == 'FoamFile':
        continue
    n = re.search(r'\bnFaces\s+(\d+)\s*;', block)
    start = re.search(r'\bstartFace\s+(\d+)\s*;', block)
    if n is None or start is None:
        continue
    n, start = int(n[1]), int(start[1])
    if n == 0:
        continue
    values = (np.zeros(n) if re.search(r'\btype\s+empty\s*;', phibc[name])
              else field(phibc[name], 'value', n))
    phi[start:start + n] = values
    patch_reports[name] = {'faces': n, 'signed_outflow_m3_s': float(values.sum()), 'sum_abs_m3_s': float(np.abs(values).sum())}
assert np.isfinite(phi).all()
cell_net = np.bincount(owner, weights=phi, minlength=ncells)-np.bincount(neighbour,weights=phi[:neighbour.size],minlength=ncells)
plan = json.loads(args.plan.read_text(encoding='utf-8'))
reports = {}
if not args.global_only:
    centres = field(read(args.case / args.time / 'C'), 'internalField', ncells, 3)
    xyz = (centres - np.asarray(args.offset)) * 1000
for room in ([] if args.global_only else plan['rooms']):
    x0, y0, x1, y1 = room['bbox']
    floor = room.get('floor_level', 450)
    ceiling = room.get('ceiling_level', 2850)
    member = ((xyz[:, 0] >= x0) & (xyz[:, 0] <= x1) & (xyz[:, 1] >= y0) & (xyz[:, 1] <= y1) &
              (xyz[:, 2] >= floor) & (xyz[:, 2] <= ceiling))
    reports[room['id']] = {'cells': int(member.sum()), **flux_report(owner, neighbour, phi, member)}
result = {'case': str(args.case.resolve()), 'time': args.time, 'cells': ncells, 'finite_phi': True,
          'mesh_owner_sha256':hashlib.sha256((mesh/'owner').read_bytes()).hexdigest(),
          'maximum_cell_flux_divergence_m3_s':float(np.abs(cell_net).max()),
          'sum_absolute_cell_flux_divergence_m3_s':float(np.abs(cell_net).sum()),
          'method': 'Conservative phi on boundary of cells whose centres lie in room bbox; discretized region may differ from exact architectural volume',
          'offset_m': args.offset, 'patches': patch_reports,
          'global': flux_report(owner, neighbour, phi, np.ones(ncells, dtype=bool)), 'rooms': reports}
args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
