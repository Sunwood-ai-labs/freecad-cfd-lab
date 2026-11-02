"""Render computed steady CFD fields and time-correct streamline particles.

Run with ParaView 6.1 pvpython.exe, through uv. No synthetic velocity field is used.
"""
from pathlib import Path
import argparse
import json
import math
import re
import subprocess
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import paraview.simple as pv
from paraview import servermanager
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('--root', required=True)
parser.add_argument('--work', required=True)
parser.add_argument('--frames', type=int, default=288)
parser.add_argument('--fps', type=int, default=24)
parser.add_argument('--time-scale', type=float, default=3.0)
parser.add_argument('--skip-encode', action='store_true')
args = parser.parse_args()
root, work = Path(args.root), Path(args.work)
work.mkdir(parents=True, exist_ok=True)
frames_dir = work / 'frames'
frames_dir.mkdir(exist_ok=True)
W, H = 1600, 1000
PW, PH = 744, 570
PANELS = [(36, 222), (820, 222)]
PARALLEL_SCALE = 4.25
FONTS = Path(r'C:\Windows\Fonts')
FONT = str(FONTS / 'YuGothM.ttc')
BOLD = str(FONTS / 'YuGothB.ttc')
NAVY = '#142c46'
TEAL = '#165e77'
BG = '#f4f7fb'
COLORS = np.array([[.267,.005,.329],[.230,.322,.546],[.128,.567,.551],[.369,.789,.383],[.993,.906,.144]])

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size=size)

def write(draw, xy, value, size=24, fill=NAVY, bold=False, **kwargs):
    draw.text(xy, value, font=font(size,bold), fill=fill, **kwargs)

def internal_grid(data):
    if data.IsA('vtkUnstructuredGrid'):
        return data
    for i in range(data.GetNumberOfBlocks()):
        block=data.GetBlock(i)
        if block is None:
            continue
        try:
            found=internal_grid(block)
            if found.GetNumberOfCells():
                return found
        except (AttributeError,ValueError):
            pass
    raise ValueError('Unable to find internal fluid mesh')

def indoor_metrics(grid, inner):
    bounds=grid.GetBounds()
    clip=vtk.vtkBoxClipDataSet()
    clip.SetInputData(grid)
    clip.SetBoxClip(inner[0],inner[1],inner[2],inner[3],bounds[4],bounds[5])
    clip.Update()
    sizes=vtk.vtkCellSizeFilter()
    sizes.SetInputConnection(clip.GetOutputPort())
    sizes.SetComputeArea(False)
    sizes.SetComputeLength(False)
    sizes.SetComputeVertexCount(False)
    sizes.SetComputeVolume(True)
    sizes.Update()
    clipped=sizes.GetOutput()
    weights=vtk_to_numpy(clipped.GetCellData().GetArray('Volume'))
    velocity=vtk_to_numpy(clipped.GetCellData().GetArray('U'))
    speeds=np.linalg.norm(velocity,axis=1)
    valid=(weights>0)&np.isfinite(speeds)
    weights,speeds=weights[valid],speeds[valid]
    volume=float(weights.sum())
    expected=(inner[1]-inner[0])*(inner[3]-inner[2])*(bounds[5]-bounds[4])
    assert abs(volume-expected)/expected < .001, (volume,expected)
    return {'indoor_area_m2':float((inner[1]-inner[0])*(inner[3]-inner[2])),
            'extrusion_depth_m':float(bounds[5]-bounds[4]),
            'clipped_volume_m3':volume,
            'area_weighted_mean_speed_m_s':float(np.average(speeds,weights=weights)),
            'area_fraction_below_0_1_m_s':float(weights[speeds<.1].sum()/volume),
            'method':'Polyhedral cells tetrahedralized without volume loss, then clipped to the room; volume-weighted original cell-speed mean; constant depth makes this area-weighted',
            'validation':'2D comparative demonstration only; no mesh independence or experimental validation'}

def traces_from_grid(grid,setup):
    west=setup['west_window_m']
    inner=setup['house_inner_m']
    bounds=grid.GetBounds()
    z=(bounds[4]+bounds[5])/2
    seed=[]
    for y in np.linspace(west[2]+.035,west[3]-.035,22):
        seed.append([west[0]+.025,float(y),z])
    for y in np.linspace(inner[2]+.25,inner[3]-.25,7):
        for x in np.linspace(inner[0]+.25,inner[1]-.25,9):
            seed.append([float(x),float(y),z])
    for y in np.linspace(setup['house_outer_m'][2]-.5,setup['house_outer_m'][3]+.5,16):
        seed.append([setup['house_outer_m'][0]-.75,float(y),z])
    pts=vtk.vtkPoints()
    for item in seed:
        pts.InsertNextPoint(*item)
    source=vtk.vtkPolyData()
    source.SetPoints(pts)
    tracer=vtk.vtkStreamTracer()
    tracer.SetInputData(grid)
    tracer.SetSourceData(source)
    tracer.SetInputArrayToProcess(0,0,0,vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS,'U')
    tracer.SetIntegratorTypeToRungeKutta45()
    tracer.SetIntegrationDirectionToForward()
    tracer.SetMaximumPropagation(45.)
    tracer.SetInitialIntegrationStep(.08)
    tracer.SetMaximumIntegrationStep(.3)
    tracer.SetMinimumIntegrationStep(.01)
    tracer.SetMaximumNumberOfSteps(14000)
    tracer.SetTerminalSpeed(.001)
    tracer.SetComputeVorticity(False)
    tracer.Update()
    output=tracer.GetOutput()
    points=vtk_to_numpy(output.GetPoints().GetData())
    times=vtk_to_numpy(output.GetPointData().GetArray('IntegrationTime'))
    lines=output.GetLines()
    ids=vtk.vtkIdList()
    paths=[]
    lines.InitTraversal()
    while lines.GetNextCell(ids):
        idx=np.array([ids.GetId(i) for i in range(ids.GetNumberOfIds())])
        t=times[idx]
        xy=points[idx,:2]
        t,unique=np.unique(t,return_index=True)
        xy=xy[unique]
        if len(t)>3 and t[-1]>.12 and np.isfinite(xy).all():
            paths.append({'t':t,'xy':xy})
    assert len(paths)>=8, f'Only {len(paths)} computed streamlines; inspect velocity data'
    return paths

def load_case(key):
    case_root=root/f'case-{key}'
    setup=json.loads((case_root/'setup.json').read_text(encoding='utf-8-sig'))
    log=(case_root/'solver-run.log').read_text(encoding='utf-8')
    assert 'SIMPLE solution converged' in log, f'Case {key} did not report convergence'
    reader=pv.OpenFOAMReader(FileName=str(case_root/'case'/'pv.foam'))
    reader.MeshRegions=['internalMesh']
    reader.CellArrays=['U','p']
    reader.Createcelltopointfiltereddata=1
    reader.UpdatePipelineInformation()
    time=float(reader.TimestepValues[-1])
    reader.UpdatePipeline(time)
    grid=internal_grid(servermanager.Fetch(reader))
    velocity=vtk_to_numpy(grid.GetPointData().GetArray('U'))
    assert np.isfinite(velocity).all()
    # vtkBoxClipDataSet silently drops polyhedral cells; convert them before
    # clipping/integration so the entire room, including near-wall cells, counts.
    tetrahedra=vtk.vtkDataSetTriangleFilter()
    tetrahedra.SetInputData(grid)
    tetrahedra.SetTetrahedraOnly(True)
    tetrahedra.Update()
    computational_grid=tetrahedra.GetOutput()
    metrics=indoor_metrics(computational_grid,setup['house_inner_m'])
    paths=traces_from_grid(computational_grid,setup)
    print('Prepared',key,grid.GetNumberOfCells(),'cells',len(paths),'paths',flush=True)
    return {'key':key,'reader':reader,'grid':grid,'time':time,'setup':setup,'metrics':metrics,'paths':paths}

pv._DisableFirstRenderCameraReset()
cases=[load_case('a'),load_case('b')]
local_max=[]
for case in cases:
    pts=vtk_to_numpy(case['grid'].GetPoints().GetData())
    U=vtk_to_numpy(case['grid'].GetPointData().GetArray('U'))
    outer=case['setup']['house_outer_m']
    cx,cy=(outer[0]+outer[1])/2,(outer[2]+outer[3])/2
    half_width=PARALLEL_SCALE*PW/PH
    mask=(pts[:,0]>cx-half_width)&(pts[:,0]<cx+half_width)&(pts[:,1]>cy-PARALLEL_SCALE)&(pts[:,1]<cy+PARALLEL_SCALE)
    local_max.append(float(np.linalg.norm(U[mask],axis=1).max()))
scale_max=math.ceil(max(local_max)*10)/10
assert 0 < scale_max < 20, 'Unexpected speed range; inspect CFD before rendering'
lut=pv.GetColorTransferFunction('U')
lut.ColorSpace='RGB'
lut.RGBPoints=[value for i,color in enumerate(COLORS) for value in [scale_max*i/4,*color]]
view=pv.GetActiveViewOrCreate('RenderView')
view.ViewSize=[PW,PH]
view.UseColorPaletteForBackground=0
view.Background=[.96,.97,.985]
view.OrientationAxesVisibility=0
view.CameraParallelProjection=1
for case in cases:
    bounds=case['grid'].GetBounds()
    outer=case['setup']['house_outer_m']
    cx=(outer[0]+outer[1])/2
    cy=(outer[2]+outer[3])/2
    z=(bounds[4]+bounds[5])/2
    case['center']=(cx,cy)
    cut=pv.Slice(Input=case['reader'])
    cut.SliceType='Plane'
    cut.SliceType.Origin=[cx,cy,z]
    cut.SliceType.Normal=[0,0,1]
    cut.UpdatePipeline(case['time'])
    display=pv.Show(cut,view)
    display.Representation='Surface'
    pv.ColorBy(display,('POINTS','U','Magnitude'))
    display.LookupTable=lut
    lut.RGBPoints=[value for i,color in enumerate(COLORS) for value in [scale_max*i/4,*color]]
    lut.RescaleTransferFunction(0,scale_max)
    display.SetScalarBarVisibility(view,False)
    if hasattr(display,'Ambient'):
        display.Ambient=1
        display.Diffuse=0
    view.ViewTime=case['time']
    view.CameraPosition=[cx,cy,z+100]
    view.CameraFocalPoint=[cx,cy,z]
    view.CameraViewUp=[0,1,0]
    view.CameraParallelScale=PARALLEL_SCALE
    pv.Render(view)
    file=work/f'field-{case["key"]}.png'
    pv.SaveScreenshot(str(file),view,ImageResolution=[PW,PH])
    case['base']=Image.open(file).convert('RGB')
    pv.SaveState(str(root/f'House-{case["key"]}-flow.pvsm'))
    pv.Hide(cut,view)

def screen(case,xy):
    s=PH/(2*PARALLEL_SCALE)
    cx,cy=case['center']
    return ((float(xy[0])-cx)*s+PW/2,PH/2-(float(xy[1])-cy)*s)

def wall_rect(draw,case,bounds,fill='#526477',width=1):
    x0,y1=screen(case,(bounds[0],bounds[2]))
    x1,y0=screen(case,(bounds[1],bounds[3]))
    draw.rectangle([x0,y0,x1,y1],fill=fill,outline=fill,width=width)

def add_walls(case,base):
    draw=ImageDraw.Draw(base)
    x0,x1,y0,y1=case['setup']['house_outer_m']
    thick=case['setup']['wall_thickness_m']
    west=case['setup']['west_window_m']
    other=case['setup']['other_window_m']
    rects=[[x0,x1,y0,y0+thick],[x0,x0+thick,y0,west[2]],[x0,x0+thick,west[3],y1]]
    if case['key']=='a':
        rects += [[x0,x1,y1-thick,y1],[x1-thick,x1,y0,other[2]],[x1-thick,x1,other[3],y1]]
    else:
        rects += [[x1-thick,x1,y0,y1],[x0,other[0],y1-thick,y1],[other[1],x1,y1-thick,y1]]
    for rect in rects:
        wall_rect(draw,case,rect)
    for window in [west,other]:
        wx0,wy1=screen(case,(window[0],window[2]))
        wx1,wy0=screen(case,(window[1],window[3]))
        draw.rectangle([wx0,wy0,wx1,wy1],outline='#00acd9',width=3)
        for x,y in [(window[0],window[2]),(window[1],window[3])]:
            px,py=screen(case,(x,y))
            draw.ellipse([px-4,py-4,px+4,py+4],fill='#00acd9')
    return base

for case in cases:
    case['base']=add_walls(case,case['base'])
    rng=np.random.default_rng(917)
    particles=[]
    for path in case['paths']:
        for _ in range(2):
            particles.append((path,float(rng.uniform(0,path['t'][-1]))))
    case['particles']=particles

def sample(path,t):
    ts=path['t']
    j=min(max(int(np.searchsorted(ts,t)),1),len(ts)-1)
    f=(t-ts[j-1])/(ts[j]-ts[j-1])
    return path['xy'][j-1]*(1-f)+path['xy'][j]*f

def panel(case,seconds):
    image=case['base'].convert('RGBA')
    layer=Image.new('RGBA',image.size,(0,0,0,0))
    draw=ImageDraw.Draw(layer)
    for path,phase in case['particles']:
        t=(phase+seconds*args.time_scale)%path['t'][-1]
        fade=min(1,t/.3,(path['t'][-1]-t)/.3)
        if fade<.05:
            continue
        xy=screen(case,sample(path,t))
        old=screen(case,sample(path,max(0,t-.16)))
        if -4<xy[0]<PW+4 and -4<xy[1]<PH+4:
            draw.line([old,xy],fill=(255,255,255,int(95*fade)),width=2)
            draw.ellipse([xy[0]-2.7,xy[1]-2.7,xy[0]+2.7,xy[1]+2.7],fill=(255,255,255,int(235*fade)),outline=(15,42,68,int(135*fade)),width=1)
    return Image.alpha_composite(image,layer).convert('RGB')

def make_frame(index):
    frame=Image.new('RGB',(W,H),BG)
    draw=ImageDraw.Draw(frame)
    write(draw,(40,24),'窓の位置で、風の通り道はどう変わる？',42,bold=True)
    write(draw,(42,91),'架空の平屋 8m × 6m｜幅1.2mの窓を2か所｜外の風は左から右へ 2 m/s',25,fill='#52677e')
    write(draw,(44,129),'形：FreeCAD  /  条件：CfdOF  /  計算：OpenFOAM  /  表示：ParaView',17,fill='#708197')
    labels=['A  向かい合う壁に窓','B  隣り合う壁に窓']
    for i,case in enumerate(cases):
        x,y=PANELS[i]
        draw.rounded_rectangle([x-8,157,x+PW+8,893],radius=20,fill='#ffffff')
        write(draw,(x+12,168),labels[i],31,fill=TEAL,bold=True)
        draw.line([(x+385,192),(x+665,192)],fill='#00a6ce',width=4)
        draw.polygon([(x+681,192),(x+661,181),(x+661,203)],fill='#00a6ce')
        frame.paste(panel(case,index/args.fps),(x,y))
        m=case['metrics']
        write(draw,(x+13,808),f'室内の平均風速  {m["area_weighted_mean_speed_m_s"]:.2f} m/s',25,bold=True)
        write(draw,(x+13,849),f'低速域（0.1m/s未満） {100*m["area_fraction_below_0_1_m_s"]:.0f} %',23,fill='#52677e')
    write(draw,(44,899),'風速 [m/s]',22,bold=True)
    for k in range(310):
        f=k/309
        color=tuple(int(v*255) for v in np.array([np.interp(f,np.linspace(0,1,5),COLORS[:,c]) for c in range(3)]))
        draw.line([(193+k,902),(193+k,924)],fill=color)
    write(draw,(165,899),'0',20)
    write(draw,(518,899),f'{scale_max:.1f}',20)
    write(draw,(635,899),f'定常解析＋粒子表示（両案共通 ×{args.time_scale:g}倍速）',23,fill=TEAL,bold=True)
    write(draw,(1340,899),'青枠が窓',23,fill='#0087ae',bold=True)
    write(draw,(44,946),'平面2Dの簡略モデル。家具・温度差を省略。実住宅の換気性能を保証する解析ではありません。',21,fill='#52677e')
    return frame

for i in range(args.frames):
    make_frame(i).save(frames_dir/f'frame-{i:04d}.png')
    if i%48==0:
        print('Frame',i,'/',args.frames,flush=True)
make_frame(args.frames//2).save(root/'comparison-poster.png')
summary={'common_speed_scale_m_s':[0,scale_max],
         'particle_method':'VTK Runge-Kutta45 streamlines from the actual steady velocity field; positions interpolated in physical IntegrationTime, never normalized to equal path duration',
         'common_time_scale':args.time_scale,'fps':args.fps,'frames':args.frames,'duration_s':args.frames/args.fps,
         'particle_caveat':'Particles show flow paths and direction; particle counts are not air-volume measurements. Paths are faded and recycled at ends.',
         'cases':{c['key']:{'latest_iteration':c['time'],'cells':c['grid'].GetNumberOfCells(),'streamlines':len(c['paths']),'turbulence_model':c['setup']['turbulence'],'source_case':str(root/f'case-{c["key"]}'/'case'),**c['metrics']} for c in cases}}
(root/'animation-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
if not args.skip_encode:
    ffmpeg='ffmpeg'
    subprocess.run([ffmpeg,'-y','-framerate',str(args.fps),'-i',str(frames_dir/'frame-%04d.png'),'-frames:v',str(args.frames),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(root/'窓配置と風通し比較.mp4')],check=True)
    subprocess.run([ffmpeg,'-y','-i',str(root/'窓配置と風通し比較.mp4'),'-vf','fps=10,scale=960:-1','-c:v','libwebp_anim','-lossless','0','-quality','65','-compression_level','6','-loop','0','-an',str(root/'preview.webp')],check=True)
print(json.dumps(summary,ensure_ascii=False),flush=True)
