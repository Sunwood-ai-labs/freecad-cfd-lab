"""Actual 3-D OpenFOAM field -> plan/3-D particle animation.

Run with ParaView pvpython via uv. No invented vector field or path geometry.
An explicit adapter JSON records coordinates and effective CFD openings.
"""
from pathlib import Path
import argparse, json, math, subprocess, hashlib
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
from PIL import Image, ImageDraw, ImageFont
import paraview.simple as pv
from paraview import servermanager

p=argparse.ArgumentParser()
p.add_argument('--root',required=True)
p.add_argument('--work',required=True)
p.add_argument('--design',required=True)
p.add_argument('--adapter',required=True)
p.add_argument('--frames',type=int,default=480)
p.add_argument('--fps',type=int,default=24)
p.add_argument('--time-scale',type=float,default=2)
p.add_argument('--prepare-only',action='store_true')
p.add_argument('--reuse',action='store_true')
p.add_argument('--geometry-only',action='store_true',help='Only save work-directory geometry previews, without simulated flow or final animation')
a=p.parse_args()
ROOT,WORK=Path(a.root),Path(a.work)
ROOT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
DESIGN=json.loads(Path(a.design).read_text(encoding='utf-8-sig'))
A=json.loads(Path(a.adapter).read_text(encoding='utf-8-sig'))
for key in ('case_file','building_shell_stl'):
    path=Path(A[key])
    A[key]=str(path if path.is_absolute() else (ROOT/path).resolve())
assert a.geometry_only or A.get('final_field_verified') is True,'Final CFD verification must be recorded before animation rendering'
OFFSET=np.array(A['offset_m'],dtype=float)
W,H=1920,1080
PX,PY,PW,PH=35,200,1280,770
SCALE=72.0
CX,CY=6.05,4.55
BG='#edf2f5';NAVY='#142d42';MUTED='#5c7080';CYAN='#00a3b5'
FONT=r'C:\Windows\Fonts\YuGothM.ttc';BOLD=r'C:\Windows\Fonts\YuGothB.ttc'
COLORS=np.array([[.267,.005,.329],[.230,.322,.546],[.128,.567,.551],[.369,.789,.383],[.993,.906,.144]])
def font(n,bold=False):return ImageFont.truetype(BOLD if bold else FONT,n)
def text(d,xy,s,n=24,c=NAVY,b=False,**kw):d.text(xy,s,font=font(n,b),fill=c,**kw)
def xy(p):return ((float(p[0])-CX)*SCALE+PW/2,PH/2-(float(p[1])-CY)*SCALE)
def rect(bounds):
    x0,y1=xy(bounds[:2]);x1,y0=xy(bounds[2:]);return [x0,y0,x1,y1]
def color(v,maxv=1.):
    f=np.clip(np.asarray(v)/maxv,0,1)
    return np.stack([np.interp(f,np.linspace(0,1,len(COLORS)),COLORS[:,k]) for k in range(3)],axis=-1)
def grid_from(data):
    if data.IsA('vtkUnstructuredGrid') and data.GetNumberOfCells():return data
    if hasattr(data,'GetNumberOfBlocks'):
        for i in range(data.GetNumberOfBlocks()):
            q=data.GetBlock(i)
            if q is None:continue
            try:return grid_from(q)
            except ValueError:pass
    raise ValueError('No internal 3D mesh')
def read_grid():
    reader=pv.OpenFOAMReader(FileName=A['case_file'])
    reader.MeshRegions=['internalMesh'];reader.CellArrays=['U','p'];reader.Createcelltopointfiltereddata=1
    reader.UpdatePipelineInformation();t=float(reader.TimestepValues[-1]);assert t>0;reader.UpdatePipeline(t)
    g=grid_from(servermanager.Fetch(reader))
    u=vtk_to_numpy(g.GetPointData().GetArray('U'))
    assert np.isfinite(u).all()
    assert g.GetBounds()[5]-g.GetBounds()[4]>3,'Expected full 3D domain'
    return g,t
def field_digest(t):
    folder=Path(A['case_file']).parent/f'{t:g}'
    u=folder/'U'
    if not u.exists():u=folder/'U.gz'
    assert u.exists(),('Latest reconstructed field missing',folder)
    return hashlib.sha256(u.read_bytes()).hexdigest()
def probe(g,xyz):
    pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(np.ascontiguousarray(xyz),deep=True))
    poly=vtk.vtkPolyData();poly.SetPoints(pts)
    pr=vtk.vtkProbeFilter();pr.SetInputData(poly);pr.SetSourceData(g);pr.Update()
    out=pr.GetOutput()
    return vtk_to_numpy(out.GetPointData().GetArray('U')),vtk_to_numpy(out.GetPointData().GetArray('vtkValidPointMask'))
def streamlines(g):
    seeds=[];seed_tags=[]
    # Window-mouth seeds at multiple real heights, plus volumetric interior seeds.
    for win in A['windows']:
        bb=win['open_bbox_m'];normal=np.array(win['inward_normal'],dtype=float)
        axis=0 if bb[3]-bb[0]>bb[4]-bb[1] else 1
        for h in np.linspace(bb[2]+.04,bb[5]-.04,4):
            for f in np.linspace(.12,.88,5):
                seed=np.array([(bb[0]+bb[3])/2,(bb[1]+bb[4])/2,h])
                seed[axis]=bb[axis]*(1-f)+bb[axis+3]*f
                seeds.append(seed+normal*.035+OFFSET)
                seed_tags.append(win['id'])
    for room in DESIGN['rooms']:
        x0,y0,x1,y1=np.array(room['bbox'])/1000
        floor=room['floor_level']/1000
        for x in np.linspace(x0+.2,x1-.2,3):
            for y in np.linspace(y0+.2,y1-.2,3):
                for z in [floor+.7,floor+1.6]:
                    seeds.append(np.array([x,y,z])+OFFSET);seed_tags.append(room['id'])
    pts=vtk.vtkPoints()
    for s in seeds:pts.InsertNextPoint(*s)
    poly=vtk.vtkPolyData();poly.SetPoints(pts)
    tr=vtk.vtkStreamTracer();tr.SetInputData(g);tr.SetSourceData(poly)
    tr.SetInputArrayToProcess(0,0,0,vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS,'U')
    tr.SetIntegratorTypeToRungeKutta45();tr.SetIntegrationDirectionToForward()
    tr.SetIntegrationStepUnit(vtk.vtkStreamTracer.LENGTH_UNIT) # metres, independent of cell size
    tr.SetMaximumPropagation(70);tr.SetInitialIntegrationStep(.025);tr.SetMinimumIntegrationStep(.002)
    tr.SetMaximumIntegrationStep(.08);tr.SetMaximumNumberOfSteps(25000);tr.SetTerminalSpeed(.002)
    tr.SetComputeVorticity(False);tr.Update();out=tr.GetOutput()
    assert out.GetNumberOfPoints()>0
    writer=vtk.vtkXMLPolyDataWriter();writer.SetFileName(str(ROOT/'computed-streamlines.vtp'));writer.SetInputData(out);assert writer.Write()==1
    xyz=vtk_to_numpy(out.GetPoints().GetData())-OFFSET
    ts=vtk_to_numpy(out.GetPointData().GetArray('IntegrationTime'))
    u=vtk_to_numpy(out.GetPointData().GetArray('U'))
    paths=[];evidence=[];ids=vtk.vtkIdList();lines=out.GetLines();lines.InitTraversal();line_id=0
    seed_ids=out.GetCellData().GetArray('SeedIds');reasons=out.GetCellData().GetArray('ReasonForTermination')
    while lines.GetNextCell(ids):
        idx=np.array([ids.GetId(j) for j in range(ids.GetNumberOfIds())]);t,un=np.unique(ts[idx],return_index=True)
        idx=idx[un];pts=xyz[idx];spd=np.linalg.norm(u[idx],axis=1)
        if len(t)>4 and t[-1]>.3 and np.linalg.norm(np.diff(pts,axis=0),axis=1).sum()>.3:
            seed_id=int(seed_ids.GetTuple1(line_id))if seed_ids is not None else -1
            tag=seed_tags[seed_id]if 0<=seed_id<len(seed_tags)else 'unknown'
            first_visits={}
            for room in DESIGN['rooms']:
                bb=np.array(room['bbox'])/1000
                hit=np.flatnonzero((pts[:,0]>bb[0])&(pts[:,0]<bb[2])&(pts[:,1]>bb[1])&(pts[:,1]<bb[3])&(pts[:,2]>room['floor_level']/1000)&(pts[:,2]<room['ceiling_level']/1000))
                if len(hit):first_visits[room['id']]=float(t[hit[0]])
            visited=sorted(first_visits,key=first_visits.get)
            evidence.append({'seed_tag':tag,'visited_room_ids':visited,'first_room_entry_time_s':first_visits,'local_z_range_m':[float(pts[:,2].min()),float(pts[:,2].max())],
                             'duration_s':float(t[-1]),'termination_reason':int(reasons.GetTuple1(line_id))if reasons is not None else None})
            paths.append({'t':t,'xyz':pts,'speed':spd,'seed_tag':tag})
        line_id+=1
    (ROOT/'streamline-evidence.json').write_text(json.dumps({'method':'Geometric room visits of actual RK45 trajectories. Counts depend on seed placement and do not measure airflow rate or ventilation efficiency.','trajectories':evidence},ensure_ascii=False,indent=2),encoding='utf-8')
    raw_count=len(paths)
    # Recycle only each visible, contiguous house segment. Physical IntegrationTime
    # differences are preserved; no equal-duration or equal-speed normalization.
    visible=[]
    for path in paths:
        q=path['xyz'];mask=(q[:,0]>-.12)&(q[:,0]<12.22)&(q[:,1]>-.12)&(q[:,1]<9.22)&(q[:,2]>.25)&(q[:,2]<2.95)
        transitions=np.diff(np.r_[0,mask.astype(int),0]);starts=np.flatnonzero(transitions==1);ends=np.flatnonzero(transitions==-1)
        for lo,hi in zip(starts,ends):
            t=path['t'][lo:hi]-path['t'][lo];xyz=path['xyz'][lo:hi]
            if len(t)>3 and t[-1]>.25 and np.linalg.norm(np.diff(xyz,axis=0),axis=1).sum()>.2:
                visible.append({'t':t,'xyz':xyz,'speed':path['speed'][lo:hi],'seed_tag':path['seed_tag']})
    assert len(visible)>30,('Insufficient actual computed visible trajectories',len(visible))
    return visible,len(seeds),raw_count
def prepare():
    g,t=read_grid();print('Read grid',g.GetNumberOfCells(),'time',t,flush=True)
    paths,n,raw_count=streamlines(g);print('Actual 3D paths',raw_count,'visible segments',len(paths),flush=True)
    xx=(np.arange(PW)-PW/2)/SCALE+CX
    yy=(PH/2-np.arange(PH))/SCALE+CY
    X,Y=np.meshgrid(xx,yy)
    Z=np.full(X.shape,1.65) # finished floor .45 + 1.2 m
    point=np.stack([X.ravel(),Y.ravel(),Z.ravel()],axis=1)+OFFSET
    vel,valid=probe(g,point)
    speed=np.linalg.norm(vel,axis=1).reshape(PH,PW)
    valid=valid.reshape(PH,PW).astype(bool)
    indoor=(X>=.2)&(X<=11.9)&(Y>=.2)&(Y<=8.9)
    select=valid&indoor
    # One non-saturating color scale for the slice and indoor 3D trajectories.
    path_max=0.
    for path in paths:
        q=path['xyz'];mask=(q[:,0]>.0)&(q[:,0]<12.1)&(q[:,1]>.0)&(q[:,1]<9.1)&(q[:,2]>.3)&(q[:,2]<2.85)
        if mask.any():path_max=max(path_max,float(path['speed'][mask].max()))
    maxv=max(.2,math.ceil(max(float(speed[select].max()),path_max)*10)/10)
    assert maxv<20,('Unexpected velocity range; review CFD',maxv)
    field=np.full((PH,PW,3),245,dtype=np.uint8)
    field[select]=(255*color(speed[select],maxv)).astype(np.uint8)
    Image.fromarray(field).save(WORK/'field.png')
    np.savez_compressed(WORK/'paths.npz',paths=np.array(paths,dtype=object))
    prep={'iteration':t,'cells':g.GetNumberOfCells(),'raw_path_count':raw_count,'path_count':len(paths),'seed_count':n,
          'slice_global_z_m':1.65+float(OFFSET[2]),'slice_local_z_m':1.65,'speed_scale_max':maxv,
          'slice_max_m_s':float(speed[select].max()),'indoor_path_max_m_s':path_max,'slice_saturated_fraction':float((speed[select]>maxv).mean()),
          'source_file':A['case_file'],'source_U_sha256':field_digest(t),'offset_m':OFFSET.tolist()}
    (WORK/'prepared.json').write_text(json.dumps(prep,indent=2),encoding='utf-8')
    return paths,prep
if a.geometry_only:
    paths=[];prep={'speed_scale_max':1.0};Image.new('RGB',(PW,PH),'#edf2f3').save(WORK/'geometry-neutral.png')
elif a.reuse:
    paths=np.load(WORK/'paths.npz',allow_pickle=True)['paths'].tolist()
    prep=json.loads((WORK/'prepared.json').read_text())
    assert prep['source_U_sha256']==field_digest(prep['iteration']),'Cached trajectories do not match source U'
else:paths,prep=prepare()
MAXV=prep['speed_scale_max']
if a.prepare_only:raise SystemExit(0)

def draw_plan():
    im=Image.open(WORK/('geometry-neutral.png' if a.geometry_only else 'field.png')).convert('RGBA');d=ImageDraw.Draw(im)
    # High windows are still marked: particles are full-3D trajectories projected on the plan.
    for wall in DESIGN['walls']:
        start=np.array(wall['start'])/1000;end=np.array(wall['end'])/1000
        th=wall['thickness']/2000
        if abs(start[0]-end[0])<1e-5:bb=[start[0]-th,min(start[1],end[1])-th,start[0]+th,max(start[1],end[1])+th]
        else:bb=[min(start[0],end[0])-th,start[1]-th,max(start[0],end[0])+th,start[1]+th]
        d.rectangle(rect(bb),fill='#344c5e')
    for op in DESIGN['openings']:
        if op['id']=='D01':continue
        x,y=np.array(op['center'])/1000;w=op['width']/1000
        if op['axis']=='x':bb=[x-w/2,y-.11,x+w/2,y+.11]
        else:bb=[x-.11,y-w/2,x+.11,y+w/2]
        if op['kind']=='window':d.rectangle(rect(bb),fill='#c5d0d5',outline='#627a86',width=2)
    for op in A.get('apertures',[]):
        if op['kind']=='window':continue
        bb=op['aperture_bbox_m'];d.rectangle(rect([bb[0],bb[1],bb[3],bb[4]]),fill='#e8eef0')
    for win in A['windows']:
        bb=win['open_bbox_m'];r=rect([bb[0],bb[1],bb[3],bb[4]])
        d.rectangle(r,fill='#ffffff',outline='#0092a5',width=3)
    # Furniture boxes are reference silhouettes; particles may pass above low furniture.
    for f in DESIGN['furniture']:
        if f.get('reference_only') or f['id'] in A.get('omitted_furniture_ids',[]):continue
        r=rect(np.array(f['bbox'])/1000)
        if r[2]-r[0]>2 and r[3]-r[1]>2:
            d.rounded_rectangle(r,radius=2,fill=(206,216,217,185),outline=(255,255,255,180),width=1)
    return im
PLAN=draw_plan()

def actor_box(bounds,col,opacity=1):
    x0,y0,z0,x1,y1,z1=bounds
    src=vtk.vtkCubeSource();src.SetBounds(x0,x1,y0,y1,z0,z1);src.Update()
    mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(src.GetOutputPort())
    ac=vtk.vtkActor();ac.SetMapper(mp);ac.GetProperty().SetColor(*col);ac.GetProperty().SetOpacity(opacity)
    return ac
def make_iso():
    renderer=vtk.vtkRenderer();renderer.SetBackground(.965,.975,.98)
    rw=vtk.vtkRenderWindow();rw.SetOffScreenRendering(1);rw.SetSize(PW,PH);rw.AddRenderer(renderer)
    # Transparent full walls clarify enclosure while leaving interior trajectories visible.
    # Exact CFD building shell, clipped only for display, preserves its openings.
    shell=vtk.vtkSTLReader();shell.SetFileName(A['building_shell_stl']);shell.Update()
    plane=vtk.vtkPlane();plane.SetOrigin(0,0,.92);plane.SetNormal(0,0,-1)
    planes=vtk.vtkPlaneCollection();planes.AddItem(plane)
    clip=vtk.vtkClipClosedSurface();clip.SetInputConnection(shell.GetOutputPort());clip.SetClippingPlanes(planes)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(clip.GetOutputPort());mapper.ScalarVisibilityOff()
    actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(.28,.37,.42);renderer.AddActor(actor)
    for room in DESIGN['rooms']:
        x0,y0,x1,y1=np.array(room['bbox'])/1000;z=room['floor_level']/1000+.002
        renderer.AddActor(actor_box([x0,y0,z-.004,x1,y1,z],[.85,.88,.88]))
    for f in A.get('furniture',[]):
        renderer.AddActor(actor_box(f['bbox_m'],[.62,.7,.7],.6))
    # Window frames at actual height, even though surrounding wall is visually cut.
    for win in A['windows']:
        bb=win['open_bbox_m'];n=np.array(win['inward_normal']);axis=0 if abs(n[1])>.5 else 1
        for z in [bb[2],bb[5]]:
            b=list(bb);b[2]=z-.018;b[5]=z+.018
            renderer.AddActor(actor_box(b,[0,.65,.72]))
        for side in [0,1]:
            b=list(bb);value=bb[axis+side*3];b[axis]=value-.018;b[axis+3]=value+.018
            renderer.AddActor(actor_box(b,[0,.65,.72]))
        if win.get('original_operation')=='awning':
            plate=actor_box([bb[0],9.085,bb[2],bb[3],9.115,bb[5]],[.05,.65,.72],.5)
            transform=vtk.vtkTransform();transform.Translate(0,9.1,bb[5]);transform.RotateX(45);transform.Translate(0,-9.1,-bb[5])
            plate.SetUserTransform(transform);renderer.AddActor(plate)
    # Real 3D streamline polylines, clipped visually to building neighbourhood.
    points=vtk.vtkPoints();lines=vtk.vtkCellArray();cols=vtk.vtkUnsignedCharArray();cols.SetNumberOfComponents(3)
    for path in paths:
        pts=path['xyz'];mask=(pts[:,0]>-.25)&(pts[:,0]<12.35)&(pts[:,1]>-.25)&(pts[:,1]<9.35)&(pts[:,2]>.25)&(pts[:,2]<2.95)
        path_colors=(color(path['speed'],MAXV)*255).astype(np.uint8)
        for i in range(len(pts)-1):
            if mask[i] and mask[i+1]:
                idx=points.GetNumberOfPoints();points.InsertNextPoint(*pts[i]);points.InsertNextPoint(*pts[i+1])
                lines.InsertNextCell(2);lines.InsertCellPoint(idx);lines.InsertCellPoint(idx+1)
                for j in [i,i+1]:cols.InsertNextTuple3(*[int(q) for q in path_colors[j]])
    poly=vtk.vtkPolyData();poly.SetPoints(points);poly.SetLines(lines);poly.GetPointData().SetScalars(cols)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly);mapper.SetColorModeToDirectScalars()
    ac=vtk.vtkActor();ac.SetMapper(mapper);ac.GetProperty().SetLineWidth(1);ac.GetProperty().SetOpacity(.33);renderer.AddActor(ac)
    cam=renderer.GetActiveCamera();cam.SetPosition(17,-12,20);cam.SetFocalPoint(6.05,4.55,.9);cam.SetViewUp(0,0,1)
    cam.ParallelProjectionOn();cam.SetParallelScale(7.5);renderer.ResetCameraClippingRange();rw.Render()
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(rw);capture.ReadFrontBufferOff();capture.Update()
    arr=vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars()).reshape(PH,PW,-1)
    im=Image.fromarray(np.flipud(arr[:,:,:3])).convert('RGBA');im.save(WORK/'iso-base.png')
    capture.SetInputBufferTypeToZBuffer();capture.Update()
    depth=np.flipud(vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars()).reshape(PH,PW)).copy()
    matrix=cam.GetCompositeProjectionTransformMatrix(PW/PH,-1,1)
    mat=np.array([[matrix.GetElement(i,j) for j in range(4)]for i in range(4)])
    def project(p):
        q=mat@np.array([*p,1]);q=q[:3]/q[3]
        return ((q[0]+1)*PW/2,(1-q[1])*PH/2)
    def hidden(p):
        q=mat@np.array([*p,1]);q=q[:3]/q[3]
        sx,sy=int((q[0]+1)*PW/2),int((1-q[1])*PH/2)
        return 0<=sx<PW and 0<=sy<PH and (q[2]+1)/2>depth[sy,sx]+.001
    project.hidden=hidden
    return im,project
ISO,ISO_PROJECT=make_iso()
if a.geometry_only:
    PLAN.save(WORK/'geometry-plan.png')

def sample(path,t):
    ts=path['t'];j=min(max(int(np.searchsorted(ts,t)),1),len(ts)-1)
    f=(t-ts[j-1])/(ts[j]-ts[j-1]);return path['xyz'][j-1]*(1-f)+path['xyz'][j]*f
rng=np.random.default_rng(7431)
PARTICLES=[]
for path in paths:
    for _ in range(2):PARTICLES.append((path,float(rng.uniform(0,path['t'][-1]))))

SHORT_NAMES={'ldk':'LDK','master':'主寝室','child1':'子ども室 1','child2':'子ども室 2','fcl':'家族収納','private_hall':'個室ホール','wash':'洗面','bath':'浴室','laundry':'ランドリー','wc':'WC','entry_hall':'ホール','entry':'玄関'}
LABELS={}
for r in DESIGN['rooms']:
    bb=np.array(r['bbox'])/1000;LABELS[r['id']]=[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2,.48]
def particles(seconds,is_iso=False):
    base=(ISO if is_iso else PLAN).copy();layer=Image.new('RGBA',base.size,(0,0,0,0));d=ImageDraw.Draw(layer)
    proj=ISO_PROJECT if is_iso else xy
    for path,phase in PARTICLES:
        t=(phase+seconds*a.time_scale)%path['t'][-1];q=sample(path,t)
        if not (-.12<q[0]<12.22 and -.12<q[1]<9.22 and .25<q[2]<2.95):continue
        fade=min(1,t/.25,(path['t'][-1]-t)/.25)
        if fade<.05:continue
        pos=proj(q);old=proj(sample(path,max(0,t-.12)))
        if not(-5<pos[0]<PW+5 and -5<pos[1]<PH+5):continue
        if is_iso and ISO_PROJECT.hidden(q):continue
        d.line([old,pos],fill=(255,255,255,int(120*fade)),width=2)
        d.ellipse([pos[0]-2.2,pos[1]-2.2,pos[0]+2.2,pos[1]+2.2],fill=(255,255,255,int(245*fade)),outline=(10,32,45,int(180*fade)),width=1)
    base=Image.alpha_composite(base,layer);d=ImageDraw.Draw(base)
    for roomid,pos in LABELS.items():
        if is_iso and roomid not in ['ldk','master','child1','child2']:continue
        sx,sy=proj(pos);name=SHORT_NAMES.get(roomid,roomid);fs=19 if roomid in ['ldk','master','child1','child2'] else 15
        box=d.textbbox((0,0),name,font=font(fs,True));tw=box[2]-box[0]
        d.rounded_rectangle([sx-tw/2-6,sy-13,sx+tw/2+6,sy+15],radius=5,fill=(255,255,255,220))
        text(d,(sx-tw/2,sy-12),name,fs,b=True)
    return base.convert('RGB')

def sidebar(d,seconds):
    X=1360
    text(d,(X,204),'窓を開けると、どこへ流れる？',25,b=True)
    text(d,(X,252),'南風 2 m/s の条件で計算',24,c=CYAN,b=True)
    for i,s in enumerate(A.get('result_lines',[])):
        text(d,(X,310+i*39),s,23,b=(i==0))
    text(d,(X,500),'計算した部屋の風速',23,b=True)
    text(d,(X,535),'空気の体積で重み付けした平均',17,c=MUTED)
    for i,r in enumerate(A.get('room_metrics',[])):
        y=578+i*48
        text(d,(X,y),r['label'],22)
        text(d,(1775,y),f"{r['mean_speed_m_s']:.2f}",24,b=True)
        text(d,(1850,y+3),'m/s',16,c=MUTED)
    text(d,(X,790),'※風速は空気の入替効率とは別の指標',18,c=MUTED)
    y=832
    text(d,(X,y),A.get('window_note','全窓開放（サッシ形式に応じて近似）'),20,c=MUTED)
    text(d,(X,y+34),A.get('door_note','室内扉は開口近似・玄関は閉鎖'),20,c=MUTED)
    text(d,(X,y+68),'家具は大物を簡略化・温度差は省略',20,c=MUTED)
    text(d,(X,y+102),'白＋青緑の枠：開いている部分',19,c=CYAN,b=True)

def make_frame(i):
    sec=i/a.fps;iso=10<=sec<16
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    text(d,(42,29),'4人家族の平屋、窓を開けたときの風の流れ',43,b=True)
    text(d,(44,99),'設計した3LDKをもとに解析｜窓の高さ・間仕切り・家具を3Dで考慮',25,c=MUTED)
    text(d,(44,143),'FreeCAD → CfdOF / OpenFOAM → ParaView / VTK',19,c=MUTED)
    d.rounded_rectangle([PX-10,PY-12,PX+PW+10,PY+PH+10],radius=18,fill='white')
    im.paste(particles(sec,iso),(PX,PY));d=ImageDraw.Draw(im)
    text(d,(63,214),'3Dの流れを斜めから見る' if iso else '北 ↑   3Dの流れを真上から見る',23,b=True)
    text(d,(63,926),'壁の上部・屋根・天井は内部を見るため表示上カット' if iso else '背景色：床上1.2mの風速  /  粒子：高さを含む3D経路の投影',20,c=MUTED)
    if not iso:
        for x in [350,650,950]:
            d.line([(x,904),(x,875)],fill=CYAN,width=4);d.polygon([(x,865),(x-7,879),(x+7,879)],fill=CYAN)
        text(d,(1000,876),'南からの風',20,c=CYAN,b=True)
    else:
        start=np.array(ISO_PROJECT([6,-1.15,.9]))+np.array([PX,PY])
        end=np.array(ISO_PROJECT([6,-.15,.9]))+np.array([PX,PY])
        vec=(end-start)/np.linalg.norm(end-start);normal=np.array([-vec[1],vec[0]])
        d.line([tuple(start),tuple(end)],fill=CYAN,width=4)
        d.polygon([tuple(end),tuple(end-vec*15+normal*7),tuple(end-vec*15-normal*7)],fill=CYAN)
        text(d,tuple(start+np.array([18,5])),'南風 2 m/s',20,c=CYAN,b=True)
        text(d,(1070,218),'北 ↗',22,c=CYAN,b=True)
    sidebar(d,sec)
    text(d,(43,995),'風速',21,b=True)
    for j in range(270):
        c=tuple(int(q) for q in color(j/269,1)*255);d.line([(113+j,997),(113+j,1018)],fill=c)
    text(d,(103,1025),'0',17,c=MUTED);text(d,(360,1025),f'{MAXV:.1f} m/s',17,c=MUTED)
    text(d,(440,994),f'白い粒子は計算した流れに沿って移動（×{a.time_scale:g}倍速）',23,b=True)
    text(d,(440,1030),'定常3D解析の可視化。粒子数は風量を表しません。メッシュ独立性・実測との一致は未検証。',18,c=MUTED)
    text(d,(1630,1000),f'{sec:04.1f} / {a.frames/a.fps:.0f} 秒',21,c=MUTED)
    if a.geometry_only:
        d.rounded_rectangle([1344,300,1895,425],radius=12,fill='white')
        text(d,(1365,320),'解析前のレイアウト確認',25,c=CYAN,b=True)
        text(d,(1365,365),'流れ・解析数値は未表示',22,c=MUTED)
    return im

if a.geometry_only:
    make_frame(0).save(WORK/'layout-plan.png');make_frame(int(13*a.fps)).save(WORK/'layout-iso.png')
    raise SystemExit(0)

outfile=ROOT/'この家の風の流れ_3D-CFD.mp4'
cmd=['ffmpeg','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(a.fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(outfile)]
log=(WORK/'ffmpeg-encode.log').open('wb')
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
for i in range(a.frames):
    frame=make_frame(i);proc.stdin.write(frame.tobytes())
    if i in [0,a.frames//4,a.frames//2,int(13*a.fps),a.frames-1]:frame.save(WORK/f'frame-{i:04d}.png')
    if i%48==0:print('Frame',i,'/',a.frames,flush=True)
proc.stdin.close();code=proc.wait();log.close();assert code==0
make_frame(int(6*a.fps)).save(ROOT/'poster.png');make_frame(int(13*a.fps)).save(ROOT/'3D-flow.png')
subprocess.run(['ffmpeg','-y','-i',str(outfile),'-vf','fps=8,scale=960:-1','-c:v','libwebp_anim','-quality','62','-compression_level','6','-loop','0','-an',str(ROOT/'preview.webp')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
summary={**prep,'frames':a.frames,'fps':a.fps,'duration_s':a.frames/a.fps,'resolution':[W,H],'time_scale':a.time_scale,
         'method':'VTK RK45 actual 3D steady U streamlines, cropped to contiguous visible house segments. Positions linearly interpolated in physical IntegrationTime; no per-path speed normalization. Recycled with phase and endpoint fade.',
         'integrator_settings':{'velocity':'point-interpolated OpenFOAM U','integration_step_unit':'metres','initial_step_m':.025,'minimum_step_m':.002,'maximum_step_m':.08,'maximum_raw_propagation_m':70,'terminal_speed_m_s':.002},
         'views':'0-10s top projection, 10-16s oblique 3D cutaway, 16-20s top projection. Display cuts do not affect CFD geometry.',
         'slice_caveat':'Plan background is U magnitude at local z=1.65m; particles use full 3D U at multiple heights. Some paths lie above low furniture.',
         'speed_scale_clipping':'Display ceiling rounded above maximum of all indoor trajectory speeds and the displayed slice; no saturation of included indoor data.',
         'particle_caveat':'Number/density of display particles does not measure volume flux or ACH.',
         'adapter_sha256':hashlib.sha256(Path(a.adapter).read_bytes()).hexdigest(),
         'source_design_sha256':hashlib.sha256(Path(a.design).read_bytes()).hexdigest()}
(ROOT/'animation-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False),flush=True)
