"""Conservative volume-weighted cell-speed summaries and reference window-plane integrals.
Run in ParaView pvpython, via uv. Window integrals interpolate U and are explicitly
separate from OpenFOAM's conservative face phi balance.
"""
from pathlib import Path
import json,argparse,hashlib
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import paraview.simple as pv
from paraview import servermanager
p=argparse.ArgumentParser();p.add_argument('--root',required=True)
p.add_argument('--time',type=float,default=None,help='Read one reconstructed iteration, instead of latest')
p.add_argument('--output',default=None,help='Explicit destination for diagnostic snapshots, kept outside final outputs')
a=p.parse_args();root=Path(a.root)
s=json.loads((root/'setup.json').read_text(encoding='utf-8-sig'))
def internal(d):
    if d.IsA('vtkUnstructuredGrid')and d.GetNumberOfCells():return d
    if hasattr(d,'GetNumberOfBlocks'):
        for i in range(d.GetNumberOfBlocks()):
            b=d.GetBlock(i)
            if b is None:continue
            try:return internal(b)
            except ValueError:pass
    raise ValueError('No internal grid')
r=pv.OpenFOAMReader(FileName=str(root/'case/pv.foam'));r.MeshRegions=['internalMesh'];r.CellArrays=['U','p'];r.Createcelltopointfiltereddata=1
r.UpdatePipelineInformation();time=float(r.TimestepValues[-1])if a.time is None else a.time
assert time>0 and any(abs(float(t)-time)<1e-8 for t in r.TimestepValues),('Requested field missing',time,list(r.TimestepValues))
r.UpdatePipeline(time);grid=internal(servermanager.Fetch(r))
assert np.isfinite(vtk_to_numpy(grid.GetCellData().GetArray('U'))).all()
print('Read actual field',time,'cells',grid.GetNumberOfCells(),flush=True)
def asvtkbounds(bb):return [bb[0],bb[3],bb[1],bb[4],bb[2],bb[5]]
def roi(bb):
    region=vtk.vtkBox();region.SetBounds(*asvtkbounds(bb))
    ex=vtk.vtkExtractGeometry();ex.SetInputData(grid);ex.SetImplicitFunction(region);ex.ExtractInsideOn();ex.ExtractBoundaryCellsOn();ex.Update()
    return ex.GetOutput()
def union_volume(boxes,room):
    boxes=[np.array([max(room[i],bb[i])for i in range(3)]+[min(room[i+3],bb[i+3])for i in range(3)])for bb in boxes]
    boxes=[bb for bb in boxes if np.all(bb[3:]>bb[:3])]
    if not boxes:return 0.
    coords=[np.unique([x for bb in boxes for x in [bb[i],bb[i+3]]])for i in range(3)]
    volume=0.
    for ix in range(len(coords[0])-1):
        x0,x1=coords[0][ix:ix+2]
        for iy in range(len(coords[1])-1):
            y0,y1=coords[1][iy:iy+2]
            for iz in range(len(coords[2])-1):
                z0,z1=coords[2][iz:iz+2];mid=np.array([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2])
                if any(np.all(mid>bb[:3])and np.all(mid<bb[3:])for bb in boxes):volume+=(x1-x0)*(y1-y0)*(z1-z0)
    return volume
rooms=[]
for room in s['rooms']:
    bb=room['bbox_m'];local=roi([bb[0]-.02,bb[1]-.02,bb[2]-.02,bb[3]+.02,bb[4]+.02,bb[5]+.02])
    # Polyhedron clipping can silently lose cells: tetrahedralize before clipping.
    tet=vtk.vtkDataSetTriangleFilter();tet.SetInputData(local);tet.SetTetrahedraOnly(True);tet.Update()
    clip=vtk.vtkBoxClipDataSet();clip.SetInputConnection(tet.GetOutputPort());clip.SetBoxClip(*asvtkbounds(bb));clip.Update()
    sizes=vtk.vtkCellSizeFilter();sizes.SetInputConnection(clip.GetOutputPort());sizes.SetComputeArea(False);sizes.SetComputeLength(False);sizes.SetComputeVolume(True);sizes.Update()
    out=sizes.GetOutput();weights=vtk_to_numpy(out.GetCellData().GetArray('Volume'));u=vtk_to_numpy(out.GetCellData().GetArray('U'))
    speed=np.linalg.norm(u,axis=1);valid=(weights>0)&np.isfinite(speed);weights=weights[valid];speed=speed[valid]
    volume=float(weights.sum());solid=union_volume([f['bbox_m']for f in s['furniture']],bb)
    expected=float(np.prod(np.array(bb[3:])-bb[:3])-solid);error=(volume-expected)/expected
    metric={'id':room['id'],'name':room['name'],'clipped_air_volume_m3':volume,'analytic_air_volume_m3':expected,'furniture_solid_volume_m3':solid,'relative_volume_error':error,
            'volume_weighted_mean_speed_m_s':float(np.average(speed,weights=weights)),'volume_fraction_below_0_1_m_s':float(weights[speed<.1].sum()/volume),
            'maximum_cell_speed_m_s':float(speed.max()),'clipped_tetrahedra':out.GetNumberOfCells()}
    rooms.append(metric);print(json.dumps(metric,ensure_ascii=False),flush=True)

def positive_linear_integral(points,values):
    # Clip a triangle by a scalar's zero contour, integrate the positive linear
    # interpolant over the resulting polygon using exact triangular integration.
    poly=list(zip(points,values));result=[]
    for j in range(len(poly)):
        p0,s0=poly[j-1];p1,s1=poly[j]
        if (s0>=0)!=(s1>=0):
            t=s0/(s0-s1);result.append((p0+t*(p1-p0),0.))
        if s1>=0:result.append((p1,s1))
    integral=0.
    if len(result)>=3:
        for j in range(1,len(result)-1):
            pts=np.array([result[0][0],result[j][0],result[j+1][0]])
            vals=[result[0][1],result[j][1],result[j+1][1]]
            area=np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))/2
            integral+=area*sum(vals)/3
    return integral
normals={'ext_south':[0,1,0],'ext_north':[0,-1,0],'ext_west':[1,0,0],'ext_east':[-1,0,0]}
windows=[]
for op in s['apertures']:
    if op['kind']!='window':continue
    bb=op['aperture_bbox_m'];pad=.25
    local=roi([bb[i]-pad for i in range(3)]+[bb[i+3]+pad for i in range(3)])
    plane=vtk.vtkPlane();origin=np.array([(bb[i]+bb[i+3])/2 for i in range(3)]);axis={'x':0,'y':1,'z':2}[op['plane_axis']];origin[axis]=op['plane_coordinate_m']
    normal=np.zeros(3);normal[axis]=1;plane.SetOrigin(*origin);plane.SetNormal(*normal)
    cut=vtk.vtkCutter();cut.SetInputData(local);cut.SetCutFunction(plane);cut.Update()
    region=vtk.vtkBox();region.SetBounds(*asvtkbounds(bb));clip=vtk.vtkClipPolyData();clip.SetInputConnection(cut.GetOutputPort());clip.SetClipFunction(region);clip.InsideOutOn();clip.Update()
    tri=vtk.vtkTriangleFilter();tri.SetInputConnection(clip.GetOutputPort());tri.Update();out=tri.GetOutput()
    pts=vtk_to_numpy(out.GetPoints().GetData());u=vtk_to_numpy(out.GetPointData().GetArray('U'));inward=np.array(normals[op['host']]);vn=u@inward
    area=qin=qout=net=0.
    for j in range(out.GetNumberOfCells()):
        cell=out.GetCell(j)
        if cell.GetNumberOfPoints()!=3:continue
        ids=np.array([cell.GetPointId(k)for k in range(3)]);xyz=pts[ids];values=vn[ids]
        ar=np.linalg.norm(np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]))/2
        area+=ar;net+=ar*float(values.mean());qin+=positive_linear_integral(xyz,values);qout+=positive_linear_integral(xyz,-values)
    assert abs(net-(qin-qout))<1e-8
    metric={'id':op['id'],'connects':op['connects'],'plane_axis':op['plane_axis'],'plane_coordinate_m':op['plane_coordinate_m'],
            'integrated_mesh_area_m2':area,'geometric_aperture_area_m2':op['area_m2'],'relative_area_error':(area-op['area_m2'])/op['area_m2'],
            'inward_reference_flux_m3_s':qin,'outward_reference_flux_m3_s':qout,'net_inward_reference_flux_m3_s':net,'net_direction':'inflow'if net>0 else 'outflow'}
    windows.append(metric);print(json.dumps(metric,ensure_ascii=False),flush=True)
totalin=sum(q['inward_reference_flux_m3_s']for q in windows);totalout=sum(q['outward_reference_flux_m3_s']for q in windows)
u_file=root/'case'/f'{time:g}'/'U'
if not u_file.exists():u_file=u_file.with_name('U.gz')
result={'status':'postprocessing_only; solver convergence is verified separately','source_iteration':time,'source_U_sha256':hashlib.sha256(u_file.read_bytes()).hexdigest(),'source_cells':grid.GetNumberOfCells(),'room_method':'Original cell-centered |U| copied to tetrahedra, clipped to exact clear room bbox, volume weighted. Polyhedra tetrahedralized first to avoid clipping loss. Furniture union volume subtracted analytically for mesh-volume consistency check.',
        'room_metric_limitations':'Speed/low-speed volume are not fresh-air replacement, contaminant removal, ACH or a health/comfort criterion.',
        'rooms':rooms,'windows':windows,
        'window_method':'vtkCutter at wall-centre plane, clipped to real aperture bbox. Point-interpolated U integrated over triangular faces; positive/negative normal flux split by exact clipping of the linear scalar on each triangle.',
        'window_flux_limitations':'Reference interpolated plane flux, not OpenFOAM conservative face phi. Sash/mesh geometry causes aperture area differences. Do not use for conservation certification or product airflow rating.',
        'reference_flux_totals':{'inward_m3_s':totalin,'outward_m3_s':totalout,'relative_difference':abs(totalin-totalout)/max(totalin,totalout)},
        'max_room_volume_relative_error':max(abs(q['relative_volume_error'])for q in rooms),
        'max_window_area_relative_error':max(abs(q['relative_area_error'])for q in windows)}
dest=Path(a.output)if a.output else root/'room-and-window-metrics.json';dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result['reference_flux_totals']),flush=True)
