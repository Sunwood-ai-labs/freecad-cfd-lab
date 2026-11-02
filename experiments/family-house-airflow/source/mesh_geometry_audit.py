"""Read-only VTK cell and boundary audit of current reconstructed mesh."""
import json
import argparse
import hashlib
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'experiments/family-house-airflow'
setup = json.loads((OUT / 'setup.json').read_text(encoding='utf-8'))
reader = vtk.vtkOpenFOAMReader()
parser=argparse.ArgumentParser();parser.add_argument('--case',type=Path,default=OUT/'case');args=parser.parse_args()
reader.SetFileName(str(args.case/'pv.foam'))
reader.UpdateInformation()
reader.EnableAllPatchArrays()
reader.DisableAllCellArrays()
reader.Update()
blocks = {}
def walk(mb):
    for i in range(mb.GetNumberOfBlocks()):
        child = mb.GetBlock(i)
        name = mb.GetMetaData(i).Get(vtk.vtkCompositeDataSet.NAME())
        if isinstance(child, vtk.vtkMultiBlockDataSet):
            walk(child)
        elif child is not None:
            blocks[name] = child
walk(reader.GetOutput())
print({k: (v.GetNumberOfPoints(), v.GetNumberOfCells()) for k, v in blocks.items()})
grid = blocks['internalMesh']
assert grid.GetNumberOfCells()>0, 'Mesh must load before geometry checks'
centres = vtk.vtkCellCenters()
centres.SetInputData(grid)
centres.Update()
xyz = vtk_to_numpy(centres.GetOutput().GetPoints().GetData())
size = vtk.vtkCellSizeFilter()
size.SetInputData(grid)
size.ComputeVolumeOn()
size.Update()
vol = vtk_to_numpy(size.GetOutput().GetCellData().GetArray('Volume'))
rooms = {}
for r in setup['rooms']:
    b = r['bbox_m']
    mask = np.logical_and(xyz >= b[:3], xyz <= b[3:]).all(axis=1)
    # Extract intersecting cells first, then tetrahedralize before precise box
    # clipping. Direct vtkBoxClipDataSet on polyhedra can silently lose volume.
    bounds = [b[0],b[3],b[1],b[4],b[2],b[5]]
    implicit=vtk.vtkBox();implicit.SetBounds(*bounds)
    extract=vtk.vtkExtractGeometry();extract.SetInputData(grid);extract.SetImplicitFunction(implicit)
    extract.ExtractInsideOn();extract.ExtractBoundaryCellsOn();extract.Update()
    tetra=vtk.vtkDataSetTriangleFilter();tetra.SetInputConnection(extract.GetOutputPort());tetra.Update()
    clip=vtk.vtkBoxClipDataSet();clip.SetInputConnection(tetra.GetOutputPort());clip.SetBoxClip(*bounds);clip.GenerateClippedOutputOff();clip.Update()
    cs=vtk.vtkCellSizeFilter();cs.SetInputConnection(clip.GetOutputPort());cs.ComputeVolumeOn();cs.Update()
    clipped_vol=float(vtk_to_numpy(cs.GetOutput().GetCellData().GetArray('Volume')).sum())
    exact_room_vol=(b[3]-b[0])*(b[4]-b[1])*(b[5]-b[2])
    furniture_vol=0
    for f in setup['furniture']:
        if f['room'] != r['id']: continue
        fb=f['bbox_m']
        lengths=[max(0,min(b[i+3],fb[i+3])-max(b[i],fb[i])) for i in range(3)]
        furniture_vol+=float(np.prod(lengths))
    expected=exact_room_vol-furniture_vol
    rooms[r['id']] = {'cells': int(mask.sum()), 'cell_center_selected_volume_m3': float(vol[mask].sum()),
        'precise_box_clipped_mesh_volume_m3':clipped_vol,'analytic_room_minus_furniture_m3':expected,
        'relative_volume_error':(clipped_vol-expected)/expected}

locator = vtk.vtkStaticCellLocator()
locator.SetDataSet(grid)
locator.BuildLocator()
checks = []
def point(label, xyz, expected):
    fluid = locator.FindCell(xyz) >= 0
    checks.append({'label': label, 'point_m': xyz, 'expected_fluid': expected, 'actual_fluid': bool(fluid), 'pass': bool(fluid) == expected})

for r in setup['rooms']:
    x0,y0,z0,x1,y1,z1 = r['bbox_m']
    x,y = (x0+x1)/2, (y0+y1)/2
    point(r['id'] + ': upper_air', [x,y,z1-.07], True)
    point(r['id'] + ': ceiling_sealed', [x,y,z1+.07], False)
    point(r['id'] + ': floor_sealed', [x,y,z0-.07], False)
point('closed_entrance', [5.9,9.0,1.4], False)
for a in setup['apertures']:
    if a['kind'] != 'window':
        continue
    b = a['aperture_bbox_m']
    p = [(b[i]+b[i+3])/2 for i in range(3)]
    point(a['id'] + ': aperture_not_plugged', p, True)
    if a['original_operation'] == 'sliding':
        shift_axis = 0 if a['axis'] == 'x' else 1
        p2 = p.copy()
        p2[shift_axis] += a['clear_width_m']
        point(a['id'] + ': retained_glass_closed', p2, False)
for f in setup['furniture']:
    if f['kind']=='wardrobe' and f['id'] in ['fcl_storage','master_closet','child1_closet','child2_closet']:
        b=f['bbox_m'];point(f['id']+': top_air_gap',[(b[0]+b[3])/2,(b[1]+b[4])/2,b[5]+.1],True)
    if f['kind'] not in ['dining_table','desk','counter']:
        continue
    b=f['bbox_m']; p=[(b[i]+b[i+3])/2 for i in range(3)]
    point(f['id'] + ': thin_top_retained', p, False)
    p2=p.copy();p2[2]=b[2]-.1
    point(f['id'] + ': open_below_top', p2, True)
for a in setup['apertures']:
    if a['original_operation'] != 'awning':
        continue
    b=a['aperture_bbox_m'];x=(b[0]+b[3])/2
    ztop=b[5]; h=a['clear_height_m']
    # The 45degree flap's mid-plane, halfway along the original leaf.
    point(a['id'] + ': flap_retained', [x,9.1+h/2/np.sqrt(2),ztop-h/2/np.sqrt(2)], False)
    point(a['id'] + ': gap_beneath_flap', [x,9.1+h/2/np.sqrt(2),ztop-h/2/np.sqrt(2)-.1], True)
result={'source_case':str(args.case.resolve()),'mesh_owner_sha256':hashlib.sha256((args.case/'constant/polyMesh/owner').read_bytes()).hexdigest(),
        'mesh_cells':grid.GetNumberOfCells(),'mesh_volume_m3':float(vol.sum()),'rooms':rooms,
        'point_checks':checks,'point_check_pass_count':sum(c['pass'] for c in checks),
        'point_check_total':len(checks),'failed':[c for c in checks if not c['pass']],
        'scope':'Independent cell locator on actual OpenFOAM mesh; finite point sampling is not exhaustive leak proof. Room volume uses cell centres and includes boundary approximation error.'}
Path(__file__).with_name('mesh-geometry-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
