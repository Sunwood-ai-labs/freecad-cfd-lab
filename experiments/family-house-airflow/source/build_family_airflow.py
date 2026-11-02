from pathlib import Path
import json, math, hashlib, time
import FreeCAD as App, FreeCADGui as Gui, Part, MeshPart
from CfdOF import CfdTools, CfdAnalysis
from CfdOF.Solve import CfdPhysicsSelection, CfdFluidMaterial, CfdInitialiseFlowField, CfdSolverFoam, CfdFluidBoundary, CfdCaseWriterFoam
from CfdOF.Mesh import CfdMesh, CfdMeshRefinement, CfdMeshTools

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'experiments/family-house-airflow'
OUT.mkdir(parents=True,exist_ok=True)
design_path=ROOT/'experiments/family-house/house-design.json'
D=json.loads(design_path.read_text(encoding='utf-8'))
def box(bb):
    x0,y0,z0,x1,y1,z1=bb
    return Part.makeBox(x1-x0,y1-y0,z1-z0,App.Vector(x0,y0,z0))
def mm_to_m(bb): return [v/1000 for v in bb]
def feat(doc,name,shape):
    ob=doc.addObject('PartDesign::Feature',name);ob.Shape=shape;return ob

doc=App.newDocument('FamilyHouseCFD')
doc.Label='4-person house - 3D open-window CFD'
# Fill all sub-floor and attic volumes with impermeable material: only the actual
# room voids communicate, so there is no artificial leakage below floors/ceiling.
building=box([0,0,0,12100,9100,3150])
for room in D['rooms']:
    x0,y0,x1,y1=room['bbox']
    building=building.cut(box([x0,y0,room['floor_level'],x1,y1,room['ceiling_level']]))
wall_by_id={w['id']:w for w in D['walls']}
openings=[]
for o in D['openings']:
    if o['id']=='D01': continue
    w=wall_by_id[o['host']]; x,y=o['center'];t=w['thickness'];fr=o['frame_width']
    if o['kind']=='window':
        h=o['height']-2*fr;full=o['width']-2*fr
        width=full/2 if o['operation']=='sliding' else full
        lo=(x if o['axis']=='x' else y)-full/2
        hi=lo+width
        z0=450+o['sill']+fr;z1=z0+h
    else:
        width=o.get('clear_width_target',o['width'])
        lo=(x if o['axis']=='x' else y)-width/2;hi=lo+width
        z0=450+o['sill']; z1=450+o['sill']+o['height']-fr
    if o['axis']=='x': bb=[lo,y-t/2-10,z0,hi,y+t/2+10,z1]
    else: bb=[x-t/2-10,lo,z0,x+t/2+10,hi,z1]
    building=building.cut(box(bb))
    entry={'id':o['id'],'name':o['name'],'kind':o['kind'],'host':o['host'],'axis':o['axis'],
        'original_operation':o['operation'],'connects':o['connects'],
        'clear_width_m':width/1000,'clear_height_m':(z1-z0)/1000,
        'aperture_bbox_m':mm_to_m(bb),'plane_coordinate_m':(y if o['axis']=='x' else x)/1000,
        'plane_axis':'y' if o['axis']=='x' else 'x','area_m2':width*(z1-z0)/1e6,
        'surrogate':False,'opening_side':'negative coordinate half' if o['operation']=='sliding' else 'whole frame opening'}
    openings.append(entry)
# 45-degree top-hung window leaves at their actual north external faces. 30mm
# rectangular ideal leaf is not a selected manufacturer's sash or hinge product.
flaps=[]
for entry in openings:
    if entry['original_operation']!='awning': continue
    bb=[v*1000 for v in entry['aperture_bbox_m']]
    x0,_,z0,x1,_,z1=bb
    plate=box([x0,9085,z0,x1,9115,z1])
    plate.rotate(App.Vector(0,9100,z1),App.Vector(1,0,0),45)
    flaps.append(plate)
    entry['flap_angle_degrees']=45
    entry['flap_thickness_m']=.03
    entry['flap_bbox_m']=mm_to_m([plate.BoundBox.XMin,plate.BoundBox.YMin,plate.BoundBox.ZMin,plate.BoundBox.XMax,plate.BoundBox.YMax,plate.BoundBox.ZMax])
    feat(doc,entry['id']+'_OpenFlap',plate).Visibility=False
# Source roof is kept exact rather than replacing the original hip roof.
src=next((d for d in App.listDocuments().values() if d.FileName.replace('\\','/').endswith('Family-House/4人家族の平屋_BIM.FCStd')),None)
if src is None: src=App.openDocument(str(ROOT/'experiments/family-house/4人家族の平屋_BIM.FCStd'))
roof=src.getObject('Roof001').Shape.copy()
App.setActiveDocument(doc.Name)
building=building.fuse(roof)
for plate in flaps: building=building.fuse(plate)
building=building.removeSplitter()
assert building.isValid()
shell=feat(doc,'BuildingEnvelope',building)
shell.ViewObject.ShapeColor=(.8,.8,.82)

# Major furniture is represented with its original footprint and height.
# Tables/desks are thin tops, avoiding a false solid wall under their legs.
# Chairs, fine rails, stroller and reference-only bathroom marker are omitted.
furniture=[];solids=[]
omitted=[]
for f in D['furniture']:
    if f.get('reference_only') or f['kind'] in ['chair','drying_rail','stroller']:
        omitted.append(f['id']);continue
    x0,y0,x1,y1=f['bbox'];z0=450+f.get('z',0);z1=z0+f['height']
    if f['kind'] in ['dining_table','desk','counter']: z0=z1-80
    # The stacked dryer is combined with washer to remove a non-physical 20mm
    # gap that cannot be resolved at this mesh scale.
    if f['kind']=='dryer': z0=450+900
    shape=box([x0,y0,z0,x1,y1,z1]);solids.append(shape)
    furniture.append({'id':f['id'],'name':f['name'],'room':f['room'],'kind':f['kind'],'bbox_m':mm_to_m([x0,y0,z0,x1,y1,z1])})
    ob=feat(doc,'Furniture_'+f['id'],shape);ob.ViewObject.ShapeColor=(.65,.6,.5);ob.Visibility=False
obstacles=building
for s in solids: obstacles=obstacles.fuse(s)
obstacles=obstacles.removeSplitter()
assert obstacles.isValid()
domain_mm=[-25000,-25000,0,37100,59100,25000]
air=box(domain_mm).cut(obstacles).removeSplitter()
sealed_air_volumes_m3=[s.Volume/1e9 for s in air.Solids if s.Volume < max(t.Volume for t in air.Solids)]
# The real hollow hip roof encloses an unvented attic above the sealed ceiling.
# This isolated trapped volume is excluded from the connected wind domain.
air=max(air.Solids,key=lambda s:s.Volume)
assert air.isValid() and len(air.Solids)==1, (air.isValid(),len(air.Solids))
fluid=feat(doc,'AirDomain',air);fluid.Visibility=False
doc.recompute()
analysis=CfdAnalysis.makeCfdAnalysis('CfdAnalysis');CfdTools.setActiveAnalysis(analysis);analysis.OutputPath=str(OUT)
physics=CfdPhysicsSelection.makeCfdPhysicsSelection();analysis.addObject(physics)
physics.Time='Steady';physics.Flow='Isothermal';physics.Turbulence='RANS';physics.TurbulenceModel='kEpsilon'
physics.gx='0 mm/s^2';physics.gy='0 mm/s^2';physics.gz='0 mm/s^2'
material=CfdFluidMaterial.makeCfdFluidMaterial('AirProperties');analysis.addObject(material)
material.Material={'Name':'Air','Density':'1.20 kg/m^3','DynamicViscosity':'1.80e-5 kg/m/s','MolarMass':'0.0289643897748887 kg/mol','Cp':'1004.703 J/kg/K','SutherlandConstant':'1.4579326545176254e-06 kg/m/s/K^0.5','SutherlandTemperature':'110.4 K'}
initial=CfdInitialiseFlowField.makeCfdInitialFlowField();analysis.addObject(initial)
solver=CfdSolverFoam.makeCfdSolverFoam();analysis.addObject(solver)
solver.Parallel=False;solver.ConvergenceTol=1e-4;solver.MaxIterations=6000;solver.SteadyWriteInterval=500
solver.URelaxation=.4;solver.pRelaxation=.15;solver.TurbulenceRelaxation=.4
mesh=CfdMesh.makeCfdMesh('AirMesh');mesh.Part=fluid;analysis.addObject(mesh)
mesh.MeshUtility='cfMesh';mesh.ElementDimension='3D';mesh.CharacteristicLengthMax='2000 mm'
mesh.CellsBetweenLevels=3;mesh.EdgeRefinement=1
mesh.PointInMesh={'x':'-10000 mm','y':'-10000 mm','z':'10000 mm'}
faces={k:[] for k in ['windInlet','windOutlet','farfield','ground','houseWalls']}
for i,face in enumerate(air.Faces,1):
    bb=face.BoundBox;c=face.CenterOfMass
    if bb.YLength<1e-5 and abs(c.y+25000)<1e-4: k='windInlet'
    elif bb.YLength<1e-5 and abs(c.y-59100)<1e-4: k='windOutlet'
    elif bb.ZLength<1e-5 and abs(c.z)<1e-4: k='ground'
    elif (bb.XLength<1e-5 and (abs(c.x+25000)<1e-4 or abs(c.x-37100)<1e-4)) or (bb.ZLength<1e-5 and abs(c.z-25000)<1e-4):k='farfield'
    else:k='houseWalls'
    faces[k].append('Face'+str(i))
assert len(faces['windInlet'])==1 and len(faces['windOutlet'])==1 and len(faces['ground'])==1
surf=CfdMeshRefinement.makeCfdMeshRefinement(mesh);surf.Label='houseSurface125mm';surf.RelativeLength=.0625;surf.RefinementThickness='180 mm';surf.NumberLayers=0
surf.ShapeRefs=[(fluid,tuple(faces['houseWalls']))]
def region(label,bb,relative):
    ob=feat(doc,label,box(bb));ob.Visibility=False
    ref=CfdMeshRefinement.makeCfdMeshRefinement(mesh);ref.Label=label+'Refinement';ref.Internal=True;ref.RelativeLength=relative;ref.ShapeRefs=[(ob,('Solid1',))]
region('NearHouse',[-1500,-1500,0,13600,10600,6500],.25)
region('Indoor',[100,100,290,12000,9000,2900],.0625)
region('FamilyCloset',[6400,100,350,8100,4300,2920],.03125)
region('WasherLeftGap',[2120,8120,370,2430,8980,2300],.015625)
region('ToiletRearGap',[4620,6970,370,5180,7180,1280],.0078125)
region('WCBasinGap',[4320,5220,370,4730,5430,1330],.0078125)
for f in furniture:
    bb=[v*1000 for v in f['bbox_m']]
    if f['kind']=='wardrobe' and 0<2850-bb[5]<=250:
        region(f['id']+'TopGap',[bb[0]-100,bb[1]-100,bb[5]-120,bb[3]+100,bb[4]+100,2920],.015625)
    elif f['kind'] in ['dining_table','desk','counter']:
        region(f['id']+'ThinTop',[bb[0]-80,bb[1]-80,bb[2]-80,bb[3]+80,bb[4]+80,bb[5]+80],.015625)
for op in openings:
    if op['kind']!='window':continue
    bb=[v*1000 for v in op['aperture_bbox_m']]
    if op['original_operation']=='awning':
        fb=[v*1000 for v in op['flap_bbox_m']]
        bb=[min(bb[i],fb[i]) for i in range(3)]+[max(bb[i+3],fb[i+3]) for i in range(3)]
        pad=120;relative=.015625
    else:pad=180;relative=.03125
    region(op['id']+'Opening',[bb[0]-pad,bb[1]-pad,bb[2]-pad,bb[3]+pad,bb[4]+pad,bb[5]+pad],relative)
def boundary(label,kind,subtype,refs):
    bc=CfdFluidBoundary.makeCfdFluidBoundary();analysis.addObject(bc);bc.Label=label;bc.BoundaryType=kind;bc.BoundarySubType=subtype;bc.ShapeRefs=[(fluid,tuple(refs))];return bc
inlet=boundary('windInlet','inlet','uniformVelocityInlet',faces['windInlet'])
inlet.VelocityIsCartesian=True;inlet.Ux='0 mm/s';inlet.Uy='2000 mm/s';inlet.Uz='0 mm/s'
inlet.TurbulenceInletSpecification='intensityAndLengthScale';inlet.TurbulenceIntensityPercentage=5;inlet.TurbulenceLengthScale='1000 mm'
outlet=boundary('windOutlet','outlet','staticPressureOutlet',faces['windOutlet']);outlet.Pressure='0 Pa'
boundary('farfield','wall','slipWall',faces['farfield'])
boundary('ground','wall','fixedWall',faces['ground'])
boundary('houseWalls','wall','fixedWall',faces['houseWalls'])
initial.PotentialFlow=True;initial.UseInletUValues=False;initial.Ux='0 mm/s';initial.Uy='2000 mm/s';initial.Uz='0 mm/s'
initial.UseOutletPValue=True;initial.BoundaryP=outlet;initial.Pressure='0 Pa';initial.UseInletTurbulenceValues=False
initial.k='15000 mm^2/s^2';initial.omega='0.2236 1/s';initial.epsilon='0.000301869 W/kg'
doc.recompute()
doc.saveAs(str(OUT/'Family-House-CFD.FCStd'))
building.exportBrep(str(OUT/'building-shell.brep'));obstacles.exportBrep(str(OUT/'obstacles.brep'));air.exportBrep(str(OUT/'air-domain.brep'))
for shape,name in [(building,'building-shell'),(obstacles,'obstacles')]:
    m=MeshPart.meshFromShape(Shape=shape,LinearDeflection=5,AngularDeflection=.25,Relative=False)
    m.transform(App.Matrix(.001,0,0,0,0,.001,0,0,0,0,.001,0,0,0,0,1));m.write(str(OUT/(name+'.stl')))
setup={'design_revision':D['design_revision'],'design_sha256':hashlib.sha256(design_path.read_bytes()).hexdigest(),'units':'m','coordinate_mapping':'CFD m = original BIM mm / 1000, no translation; north +Y; ground z=0',
    'case_dir':str(OUT/'case'),'domain_bbox_m':mm_to_m(domain_mm),'house_bbox_m':[0,0,0,12.1,9.1,5.40411],
    'wind_m_s':[0,2,0],'wind_description':'uniform external wind south to north, 2 m/s; no terrain boundary layer or neighboring buildings',
    'physics':'3D steady incompressible isothermal RANS kEpsilon','density_kg_m3':1.2,'nu_m2_s':1.5e-5,'inlet_turbulence_intensity_percent':5,'inlet_turbulence_length_scale_m':1,
    'entrance':'D01 closed and impermeable','interior_doors':'all open; door leaves and handles omitted (full-open aperture approximation)',
    'windows':'W01-W07 sliding: negative-coordinate half of frame-inner span open; W08/W09 original top-hung awning retained with ideal 45-degree 30mm-thick leaf',
    'apertures':openings,'furniture':furniture,'omitted_furniture_ids':omitted,'rooms':[{**r,'bbox_m':[r['bbox'][0]/1000,r['bbox'][1]/1000,r['floor_level']/1000,r['bbox'][2]/1000,r['bbox'][3]/1000,r['ceiling_level']/1000]} for r in D['rooms']],
    'sealed_floor_and_ceiling':True,'excluded_sealed_attic_volumes_m3':sealed_air_volumes_m3,'building_valid':building.isValid(),'obstacles_valid':obstacles.isValid(),'fluid_valid':air.isValid(),'fluid_solids':len(air.Solids),'fluid_volume_m3':air.Volume/1e9,
    'mesh_target':{'base_m':2,'indoor_m':.125,'house_surface_m':.125,'sliding_window_m':.0625,'awning_window_m':.03125,'boundary_layers':0},
    'limitations':['concept design product-independent opening dimensions','door leaves omitted','no neighboring buildings, terrain profile, vegetation, screens, rails or product hardware; exterior porch/steps omitted','no buoyancy, HVAC, thermal or contaminant transport','major furniture simplified boxes; table/desk top80mm, no legs; fine objects omitted','no experiment validation, grid-independence or domain-independence study'],
    'boundary_faces':faces,'created_at':time.strftime('%Y-%m-%dT%H:%M:%S')}
(OUT/'setup.json').write_text(json.dumps(setup,ensure_ascii=False,indent=2),encoding='utf-8')
# Windows TCP forwarding may be unavailable while the same Podman VM remains
# usable through wsl. Retain the preference-requested Docker template mode in
# memory; actual execution below is through the dedicated WSL container.
if App.ParamGet(CfdTools.getPreferencesLocation()).GetBool('UseDocker') and CfdTools.docker_container is not None:
    CfdTools.docker_container.usedocker=True
writer=CfdMeshTools.CfdMeshTools(mesh);writer.writeMesh()
CfdCaseWriterFoam.CfdCaseWriterFoam(analysis).writeCase()
scheme=OUT/'case/system/fvSchemes';txt=scheme.read_text();scheme.write_text(txt.replace('bounded Gauss linearUpwindV grad(U)','bounded Gauss upwind'))
# Mount this output folder at /tmp in a dedicated container, rather than changing
# CfdOF's saved default-output-directory preference for previous analyses.
allrun=OUT/'case/Allrun';txt=allrun.read_text();import re
txt=re.sub(r'MESHDIR="[^"]+"','MESHDIR="/tmp/meshCase"',txt);allrun.write_text(txt)
shell.Visibility=True;fluid.Visibility=False
Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll();doc.recompute();doc.save()
print('BUILT',doc.Name,air.Volume/1e9,len(air.Faces),str(OUT/'setup.json'))
