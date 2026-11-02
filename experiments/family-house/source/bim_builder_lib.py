"""Native FreeCAD BIM helpers for the four-person family-house basic design.

Coordinates and dimensional values are millimetres. This module does not create
or save a document at import time.
"""
import math
import FreeCAD as App
import Part
import Draft
import Arch
import ArchWindowPresets


def metadata(obj, name, value, description='Basic-design information'):
    if name not in obj.PropertiesList:
        obj.addProperty('App::PropertyString', name, 'Design information', description)
    setattr(obj, name, str(value))


def camera_view(doc, direction, output_path, size=(1600,1000)):
    """Direct Coin camera placement avoids FreeCAD's interpolated view animation."""
    import FreeCADGui as Gui
    from PySide import QtWidgets
    App.setActiveDocument(doc.Name)
    # Opening an FCStd with a TechDraw page can activate the paper view.
    # Explicitly activate this document's 3D subwindow before using its camera.
    for area in Gui.getMainWindow().findChildren(QtWidgets.QMdiArea):
        for sub in area.subWindowList():
            if sub.widget().metaObject().className()=='Gui::View3DInventor' and sub.windowTitle().startswith(doc.Label):
                area.setActiveSubWindow(sub)
                sub.widget().setFocus()
    QtWidgets.QApplication.processEvents()
    view=Gui.activeDocument().activeView()
    assert hasattr(view,'getCameraNode'),'No 3D camera view is active for the family-house document'
    view.setCameraType('Orthographic')
    back=App.Vector(*direction);back.normalize()
    up_hint=App.Vector(0,1,0) if abs(back.z)>.999 else App.Vector(0,0,1)
    right=up_hint.cross(back);right.normalize()
    up=back.cross(right);up.normalize()
    rotation=App.Rotation(right,up,back,'ZXY')
    bb=App.BoundBox()
    for obj in doc.Objects:
        if hasattr(obj,'Shape') and not obj.Shape.isNull() and obj.ViewObject.Visibility:
            bb.add(obj.Shape.BoundBox)
    corners=[App.Vector(x,y,z) for x in [bb.XMin,bb.XMax] for y in [bb.YMin,bb.YMax] for z in [bb.ZMin,bb.ZMax]]
    xs=[p.dot(right) for p in corners];ys=[p.dot(up) for p in corners]
    height=max(max(ys)-min(ys),(max(xs)-min(xs))*size[1]/size[0])*1.15
    center=App.Vector((bb.XMin+bb.XMax)/2,(bb.YMin+bb.YMax)/2,(bb.ZMin+bb.ZMax)/2)
    distance=max(100000,bb.DiagonalLength*5)
    position=center+back*distance
    cam=view.getCameraNode()
    cam.orientation.setValue(*rotation.Q)
    cam.position.setValue(position.x,position.y,position.z)
    cam.focalDistance.setValue(distance)
    cam.height.setValue(height)
    cam.nearDistance.setValue(max(1,distance-bb.DiagonalLength*2))
    cam.farDistance.setValue(distance+bb.DiagonalLength*2)
    Gui.Selection.clearSelection();Gui.updateGui()
    view.saveImage(str(output_path),size[0],size[1],'Current')
    return {'camera_type':'Orthographic','back_direction':[back.x,back.y,back.z],
            'up_direction':[up.x,up.y,up.z],'height_mm':height,'image_size':list(size)}


def dimension_from_envelope(doc,page,plan_view,envelope_cut,width,depth):
    """Dimension only the actual external-wall contour, excluding doors and roof."""
    import FreeCADGui as Gui
    import time
    datum=doc.getObject('BuildingDimensionReference')
    if datum is None:
        datum=doc.addObject('TechDraw::DrawViewPart','BuildingDimensionReference');page.addView(datum)
    datum.Source=[envelope_cut];datum.Direction=App.Vector(0,0,1)
    datum.X=plan_view.X;datum.Y=plan_view.Y
    datum.Caption=''
    datum.ViewObject.LineWidth=.01
    doc.recompute();Gui.updateGui()
    deadline=time.time()+30
    vertices=datum.getVisibleVertexes()
    while len(vertices)<4 and time.time()<deadline:
        Gui.updateGui();time.sleep(.05);vertices=datum.getVisibleVertexes()
    assert len(vertices)>=4,'Native wall contour has no projected vertices'
    minx,maxx=min(p.x for p in vertices),max(p.x for p in vertices)
    miny,maxy=min(p.y for p in vertices),max(p.y for p in vertices)
    ix0=min(range(len(vertices)),key=lambda i:(abs(vertices[i].x-minx),abs(vertices[i].y-miny)))
    ix1=min(range(len(vertices)),key=lambda i:(abs(vertices[i].x-maxx),abs(vertices[i].y-miny)))
    iy0=min(range(len(vertices)),key=lambda i:(abs(vertices[i].y-miny),abs(vertices[i].x-minx)))
    iy1=min(range(len(vertices)),key=lambda i:(abs(vertices[i].y-maxy),abs(vertices[i].x-minx)))
    for name,kind,indices,x,y in [('BuildingWidth','DistanceX',(ix0,ix1),plan_view.X.Value,plan_view.Y.Value+miny-13),('BuildingDepth','DistanceY',(iy0,iy1),plan_view.X.Value+minx-13,plan_view.Y.Value)]:
        dimension=doc.getObject(name)
        if dimension is None: dimension=doc.addObject('TechDraw::DrawViewDimension',name);page.addView(dimension)
        dimension.Type=kind;dimension.References2D=[(datum,tuple('Vertex'+str(i) for i in indices))]
        dimension.FormatSpec='%.3w';dimension.ShowUnits=True
        dimension.X=x;dimension.Y=y
    doc.recompute();Gui.updateGui();doc.recompute()
    actual=[doc.BuildingWidth.getRawValue(),doc.BuildingDepth.getRawValue()]
    assert abs(actual[0]-width)<1e-5 and abs(actual[1]-depth)<1e-5,('Native contour dimensions',actual,[width,depth])
    return {'source':'External-wall 1.2m cut contour only','width_mm':actual[0],'depth_mm':actual[1]}


def export_plan_svg_mm(doc,page,filename):
    """Export explicit millimetres without permanently changing global units."""
    import FreeCADGui as Gui
    import TechDrawGui
    import xml.etree.ElementTree as ET
    previous=App.Units.getSchema()
    dimensions=[o for o in doc.Objects if o.TypeId=='TechDraw::DrawViewDimension']
    for dimension in dimensions:
        dimension.Arbitrary=False;dimension.ShowUnits=True;dimension.FormatSpec='%.3w'
    try:
        App.Units.setSchema(6) # MmMin, fixed millimetres for the exported sheet.
        for dimension in dimensions: dimension.touch()
        doc.recompute();Gui.updateGui();doc.recompute()
        TechDrawGui.exportPageAsSvg(page,str(filename))
    finally:
        App.Units.setSchema(previous)
        for dimension in dimensions: dimension.touch()
        doc.recompute();Gui.updateGui();doc.recompute()
    values=[''.join(node.itertext()) for node in ET.parse(str(filename)).getroot().iter() if node.tag.endswith('text')]
    assert any('12100' in value and 'mm' in value for value in values),values
    assert any('9100' in value and 'mm' in value for value in values),values
    assert App.Units.getSchema()==previous
    return {'svg_dimensions':['12100 mm','9100 mm'],'global_schema_restored':previous,
            'fcstd_dimensions':'Live measured dimensions, Arbitrary=False, units shown individually'}


class FamilyBIM:
    def __init__(self, doc, floor_level=450, wall_height=2700):
        self.doc = doc
        self.floor_level = floor_level
        self.wall_height = wall_height
        self.walls = {}
        self.wall_data = {}
        self.openings = []
        self.spaces = []
        self.groups = {}
        for name, label in [('Structure','01 Floors and foundation reference'),
                            ('Walls','02 Native BIM walls'),
                            ('Openings','03 Native BIM doors and windows'),
                            ('Spaces','04 Native BIM room spaces'),
                            ('Furniture','05 Furniture and equipment'),
                            ('Roof','06 Native BIM roof'),
                            ('Technical','07 Linked drawing geometry')]:
            group = doc.addObject('App::DocumentObjectGroup', name)
            group.Label = label
            self.groups[name] = group

    def add_wall(self, key, bbox, thickness=None, height=None, label=None):
        x0,y0,x1,y1 = bbox
        dx,dy = x1-x0,y1-y0
        if dx >= dy:
            p0,p1 = App.Vector(x0,(y0+y1)/2,self.floor_level),App.Vector(x1,(y0+y1)/2,self.floor_level)
            width = thickness or dy
        else:
            p0,p1 = App.Vector((x0+x1)/2,y0,self.floor_level),App.Vector((x0+x1)/2,y1,self.floor_level)
            width = thickness or dx
        base = Draft.make_wire([p0,p1],closed=False)
        base.Label = key+' baseline'
        self.doc.recompute()
        wall = Arch.makeWall(base,height=height or self.wall_height,width=width,align='Center',name=label or key)
        self.doc.recompute()
        wall.ViewObject.ShapeColor = (.91,.91,.86)
        wall.ViewObject.LineColor = (.30,.32,.34)
        self.groups['Walls'].addObject(wall)
        metadata(wall,'DesignID',key)
        metadata(wall,'DesignStatus','Basic design; wall assembly and structural design not verified')
        self.walls[key] = wall
        self.wall_data[key] = {'bbox':list(bbox),'p0':p0,'p1':p1,'width':width,'height':height or self.wall_height}
        return wall

    def add_opening(self, key, host, offset, width, height, sill=0,
                    kind='window', operation='sliding', label=None, frame=50):
        wall = self.walls[host]
        data = self.wall_data[host]
        tangent = data['p1']-data['p0']
        tangent.normalize()
        vertical = App.Vector(0,0,1)
        normal = tangent.cross(vertical)
        anchor = data['p0']+tangent*offset-normal*(data['width']/2)
        anchor.z = self.floor_level+sill
        placement = App.Placement(anchor,App.Rotation(tangent,vertical,normal,'ZXY'))
        preset = ('Opening only' if kind=='passage' else 'Simple door' if kind=='door' else 'Awning' if operation=='awning' else 'Sliding 2-pane')
        before = wall.Shape.Volume
        frame_argument=max(frame,1)
        obj = ArchWindowPresets.makeWindowPreset(preset,width,height,frame_argument,frame_argument,8,
                                                min(data['width'],100),80,0,0,placement)
        obj.Label = label or key
        obj.Normal = normal
        obj.Hosts = [wall]
        obj.HoleDepth = data['width']+200
        if kind=='door':
            obj.IfcType = 'Door'
        metadata(obj,'DesignID',key)
        metadata(obj,'OpeningOperation',operation)
        metadata(obj,'RoughOpening_mm',f'{width} x {height}')
        metadata(obj,'FrameInnerSpan_mm',width-2*frame)
        metadata(obj,'ActualOpenWidth','Unverified; frame span is not actual sash/leaf opening width')
        metadata(obj,'DoorDrawingNote','Closed-state 3D geometry; operation is specified in the floor plan' if kind=='door' else 'Window frame and glazing; rough opening includes frame')
        self.groups['Openings'].addObject(obj)
        self.doc.recompute()
        bottom=self.floor_level+sill
        wall_base=data.get('z_base',self.floor_level)
        cut_height=max(0,min(bottom+height,wall_base+data['height'])-max(bottom,wall_base))
        expected = width*cut_height*data['width']
        actual = before-wall.Shape.Volume
        self.openings.append({'id':key,'host':host,'object':obj.Name,'kind':kind,
                              'rough_width_mm':width,'frame_inner_span_mm':width-2*frame,
                              'height_mm':height,'sill_mm':sill,
                              'expected_wall_cut_mm3':expected,'actual_wall_cut_mm3':actual,
                              'wall_cut_ok':abs(expected-actual)<max(1,expected*1e-6)})
        return obj

    def add_slab(self, name, bbox, top=450, thickness=200, label=None, color=(.66,.62,.54)):
        x0,y0,x1,y1 = bbox
        base = Draft.make_rectangle(x1-x0,y1-y0,placement=App.Placement(App.Vector(x0,y0,top-thickness),App.Rotation()),face=True)
        self.doc.recompute()
        slab = Arch.makeStructure(base,height=thickness,name=label or name)
        slab.IfcType = 'Slab'
        self.doc.recompute()
        slab.ViewObject.ShapeColor = color
        self.groups['Structure'].addObject(slab)
        metadata(slab,'DesignID',name)
        metadata(slab,'DesignStatus','Schematic floor build-up; structural and waterproofing specification not designed')
        return slab

    def add_space(self, name, polygon, label, ceiling_height=2400, floor_level=None):
        floor_level=self.floor_level if floor_level is None else floor_level
        pts = [App.Vector(p[0],p[1],floor_level) for p in polygon]
        if pts[0].distanceToPoint(pts[-1])>1e-6:
            pts.append(pts[0])
        unique=pts[:-1]
        xs=sorted(set(round(p.x,6) for p in unique));ys=sorted(set(round(p.y,6) for p in unique))
        if len(unique)==4 and len(xs)==2 and len(ys)==2:
            base=self.doc.addObject('Part::Box',name+'RoomVolume')
            base.Length=xs[-1]-xs[0];base.Width=ys[-1]-ys[0];base.Height=ceiling_height
            base.Placement.Base=App.Vector(xs[0],ys[0],floor_level)
        else:
            wire=Draft.make_wire(pts[:-1],closed=True,face=True)
            self.doc.recompute()
            base=self.doc.addObject('Part::Extrusion',name+'RoomVolume')
            base.Base=wire;base.Dir=App.Vector(0,0,ceiling_height);base.Solid=True
            wire.Visibility=False
        space = Arch.makeSpace(base,name=label)
        self.doc.recompute()
        space.Visibility = False
        base.Visibility = False
        metadata(space,'DesignID',name)
        metadata(space,'ClearCeilingHeight_mm',ceiling_height)
        self.groups['Spaces'].addObject(space)
        self.spaces.append({'id':name,'object':space.Name,'label':label,
                            'area_m2':space.Area.Value/1e6,'volume_m3':space.Shape.Volume/1e9})
        return space

    def add_hip_roof(self, bbox, pitch=25, overhang=450, thickness=120):
        x0,y0,x1,y1 = bbox
        z=self.floor_level+self.wall_height
        wire=Draft.make_wire([App.Vector(x0,y0,z),App.Vector(x1,y0,z),
                              App.Vector(x1,y1,z),App.Vector(x0,y1,z)],closed=True)
        self.doc.recompute()
        roof=Arch.makeRoof(wire,angles=[pitch],run=[min(x1-x0,y1-y0)/2],thickness=[thickness],overhang=[overhang],name='Hipped roof - preliminary geometry')
        self.doc.recompute()
        roof.ViewObject.ShapeColor=(.22,.27,.31)
        roof.ViewObject.LineColor=(.16,.20,.23)
        self.groups['Roof'].addObject(roof)
        metadata(roof,'DesignStatus','Roof-form proposal only; framing, snow, wind and drainage design unverified')
        return roof

    def box_component(self, name, bbox, height, z=None, color=(.70,.66,.59), group='Furniture'):
        x0,y0,x1,y1=bbox
        obj=self.doc.addObject('Part::Box',name)
        obj.Length=x1-x0;obj.Width=y1-y0;obj.Height=height
        obj.Placement.Base=App.Vector(x0,y0,self.floor_level if z is None else z)
        obj.ViewObject.ShapeColor=color
        obj.ViewObject.LineColor=(.34,.34,.34)
        self.groups[group].addObject(obj)
        return obj

    def add_bed(self, name, bbox, head='north'):
        x0,y0,x1,y1=bbox
        self.box_component(name+'Frame',bbox,230,color=(.48,.36,.25))
        self.box_component(name+'Mattress',[x0+25,y0+25,x1-25,y1-25],180,
                           z=self.floor_level+230,color=(.86,.88,.86))
        if y1-y0>=x1-x0:
            hb=[x0,y0,x1,y0+70] if head=='south' else [x0,y1-70,x1,y1]
            pillow=[x0+70,y0+100,x1-70,y0+450] if head=='south' else [x0+70,y1-450,x1-70,y1-100]
            self.box_component(name+'Headboard',hb,800,color=(.48,.36,.25))
            self.box_component(name+'Pillow',pillow,90,
                               z=self.floor_level+410,color=(.97,.96,.92))
        else:
            self.box_component(name+'Headboard',[x0,y0,x0+70,y1],800,color=(.48,.36,.25))
            self.box_component(name+'Pillow',[x0+100,y0+70,x0+450,y1-70],90,
                               z=self.floor_level+410,color=(.97,.96,.92))

    def add_desk(self, name, bbox):
        x0,y0,x1,y1=bbox
        self.box_component(name+'Top',bbox,40,z=self.floor_level+700,color=(.71,.59,.43))
        leg=45
        for i,(x,y) in enumerate([(x0+20,y0+20),(x1-leg-20,y0+20),
                                  (x0+20,y1-leg-20),(x1-leg-20,y1-leg-20)]):
            self.box_component(name+'Leg'+str(i),[x,y,x+leg,y+leg],700,color=(.36,.38,.40))

    def shape_report(self):
        records=[]
        for obj in self.doc.Objects:
            if hasattr(obj,'Shape') and not obj.Shape.isNull():
                records.append({'object':obj.Name,'label':obj.Label,'type':obj.TypeId,
                                'native_bim_type':getattr(getattr(obj,'Proxy',None),'Type',None),
                                'valid':obj.Shape.isValid(),'solids':len(obj.Shape.Solids),
                                'volume_mm3':obj.Shape.Volume})
        return {'shapes':records,'openings':self.openings,'spaces':self.spaces}

    def add_plan_page(self, bbox, room_labels=None, scale=.02, cut_height=1200):
        """Create linked native cut geometry and a dimensioned TechDraw plan."""
        import os
        import TechDraw
        x0,y0,x1,y1=bbox
        clip=self.doc.addObject('Part::Box','PlanCutVolume')
        clip.Length=x1-x0+2000;clip.Width=y1-y0+2000;clip.Height=cut_height+10
        clip.Placement.Base=App.Vector(x0-1000,y0-1000,self.floor_level-10)
        self.groups['Technical'].addObject(clip)
        visible_sources=list({o.Name:o for o in self.walls.values()}.values())+[self.doc.getObject(x['object']) for x in self.openings]
        cut_sources=[]
        for source in visible_sources:
            common=self.doc.addObject('Part::Common','PlanCut_'+source.Name)
            common.Base=source;common.Tool=clip
            self.groups['Technical'].addObject(common)
            cut_sources.append(common)
        self.doc.recompute()
        cut_sources=[o for o in cut_sources if not o.Shape.isNull()]
        cut_sources += [o for o in self.groups['Furniture'].Group if hasattr(o,'Shape') and not o.Shape.isNull()]
        page=self.doc.addObject('TechDraw::DrawPage','FloorPlan_A3')
        page.Label='家具入り平面図 1:50 - 基本設計'
        page.Scale=scale
        template=self.doc.addObject('TechDraw::DrawSVGTemplate','PlanTemplate')
        template.Template=os.path.join(App.getResourceDir(),'Mod','TechDraw','Templates','ISO','A3_Landscape_blank.svg')
        page.Template=template
        view=self.doc.addObject('TechDraw::DrawViewPart','PlanView')
        page.addView(view)
        view.Source=cut_sources
        view.Direction=App.Vector(0,0,1)
        view.X=172;view.Y=150
        self.doc.recompute()
        for source in cut_sources+[clip]: source.Visibility=False
        self.groups['Technical'].Visibility=False
        def annotation(name, lines,x,y,size=3):
            obj=self.doc.addObject('TechDraw::DrawViewAnnotation',name)
            page.addView(obj);obj.Text=lines;obj.Font='Yu Gothic UI';obj.TextSize=size;obj.X=x;obj.Y=y
            return obj
        annotation('PlanTitle',['4人家族の平屋 / 3LDK 基本設計案'],110,281,5)
        annotation('PlanStatus',['建設地・敷地・法規・構造・設備詳細は未確定 / 施工用図面ではありません'],154,17,2.7)
        for room in room_labels or []:
            cx,cy=room['center']
            annotation('Label_'+room['id'],[room['label'],f"{room['area_m2']:.2f} m2"],
                       view.X.Value+(cx-(x0+x1)/2)*scale,
                       view.Y.Value+(cy-(y0+y1)/2)*scale,2.8)
        self.doc.recompute()
        import time
        ready_deadline=time.time()+20
        vertices=view.getVisibleVertexes()
        while len(vertices)<4 and time.time()<ready_deadline:
            App.Gui.updateGui()
            time.sleep(.05)
            vertices=view.getVisibleVertexes()
        if len(vertices)>=4:
            minx,maxx=min(p.x for p in vertices),max(p.x for p in vertices)
            miny,maxy=min(p.y for p in vertices),max(p.y for p in vertices)
            ix0=min(range(len(vertices)),key=lambda i:(abs(vertices[i].x-minx),abs(vertices[i].y-miny)))
            ix1=min(range(len(vertices)),key=lambda i:(abs(vertices[i].x-maxx),abs(vertices[i].y-miny)))
            iy0=min(range(len(vertices)),key=lambda i:(abs(vertices[i].y-miny),abs(vertices[i].x-minx)))
            iy1=min(range(len(vertices)),key=lambda i:(abs(vertices[i].y-maxy),abs(vertices[i].x-minx)))
            for name,kind,indices,x,y in [
                    ('BuildingWidth','DistanceX',(ix0,ix1),view.X.Value,view.Y.Value+miny-13),
                    ('BuildingDepth','DistanceY',(iy0,iy1),view.X.Value+minx-13,view.Y.Value)]:
                dimension=self.doc.addObject('TechDraw::DrawViewDimension',name)
                page.addView(dimension);dimension.Type=kind
                dimension.References2D=[(view,tuple('Vertex'+str(i) for i in indices))]
                dimension.X=x;dimension.Y=y
        self.doc.recompute()
        return page,view
