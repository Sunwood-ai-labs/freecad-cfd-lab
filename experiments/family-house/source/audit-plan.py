from pathlib import Path
import json, math
from collections import deque
import numpy as np

src=Path(__file__).resolve().parent.parent/'house-design.json'
p=json.loads(src.read_text(encoding='utf-8-sig'))
rooms={r['id']:r for r in p['rooms']}
furn=p['furniture']

def overlap(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
def inside(b,a):
    return b[0]>=a[0]-1e-6 and b[1]>=a[1]-1e-6 and b[2]<=a[2]+1e-6 and b[3]<=a[3]+1e-6
def orientation(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def seg_cross(a,b,c,d):
    return orientation(a,b,c)*orientation(a,b,d)<-1e-6 and orientation(c,d,a)*orientation(c,d,b)<-1e-6
def point_in_polygon(q,poly):
    yes=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>q[1])!=(b[1]>q[1]) and q[0]<(b[0]-a[0])*(q[1]-a[1])/(b[1]-a[1])+a[0]: yes=not yes
    return yes
def polygon_rect(poly,b):
    corners=[(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])]
    if any(b[0]<v[0]<b[2] and b[1]<v[1]<b[3] for v in poly): return True
    if any(point_in_polygon(v,poly) for v in corners): return True
    return any(seg_cross(a,z,c,d) for a,z in zip(poly,poly[1:]+poly[:1]) for c,d in zip(corners,corners[1:]+corners[:1]))

outside=[];solid_collisions=[];arc_collisions=[]
for f in furn:
    if not inside(f['bbox'],rooms[f['room']]['bbox']): outside.append(f['id'])
for i,a in enumerate(furn):
    if a['kind']=='wet_floor': continue
    for b in furn[i+1:]:
        if b['kind']=='wet_floor': continue
        if overlap(a['bbox'],b['bbox']) and min(a['z']+a['height'],b['z']+b['height'])>max(a['z'],b['z']): solid_collisions.append([a['id'],b['id']])
for d in p['openings']:
    if not d['operation'].startswith('hinged'): continue
    h=d['hinge_point'];radius=d['clear_width_target']
    v=d['closed_vector'];w=d['open_vector']
    angle=math.atan2(v[1],v[0]);turn=1 if v[0]*w[1]-v[1]*w[0]>0 else -1
    poly=[h]+[[h[0]+radius*math.cos(angle+turn*i*math.pi/360),h[1]+radius*math.sin(angle+turn*i*math.pi/360)] for i in range(181)]
    for f in furn:
        if f['kind'] in ['wet_floor','drying_rail'] or f['z']>=d['height']: continue
        if polygon_rect(poly,f['bbox']): arc_collisions.append([d['id'],f['id']])

# Conservative 600 x 600 mm square body, all room doors at their fully-open poses.
# Windows are kept closed for this route test. It does not validate body posture,
# step negotiation, product clearances, wheelchair use or external access.
step=25;radius=300
X=np.arange(-500,12601,step);Y=np.arange(-500,10601,step)
blocked=np.zeros((len(Y),len(X)),dtype=bool)
def block(b):
    ix=np.where((X>=b[0]-radius)&(X<=b[2]+radius))[0]
    iy=np.where((Y>=b[1]-radius)&(Y<=b[3]+radius))[0]
    if len(ix) and len(iy): blocked[np.ix_(iy,ix)]=True
for wall in p['walls']:
    a,b=wall['start'],wall['end'];axis=0 if a[1]==b[1] else 1
    lo,hi=sorted([a[axis],b[axis]]);parts=[(lo,hi)]
    ds=[d for d in p['openings'] if d['host']==wall['id'] and d['kind'] in ['door','passage']]
    for d in ds:
        c=d['center'][axis];u,z=c-d['width']/2,c+d['width']/2
        nxt=[]
        for l,r in parts:
            if z<=l or u>=r: nxt.append((l,r))
            else:
                if u>l:nxt.append((l,u))
                if z<r:nxt.append((z,r))
        parts=nxt
    thick=wall['thickness']/2
    def wallbox(l,r):
        return [l,a[1]-thick,r,a[1]+thick] if axis==0 else [a[0]-thick,l,a[0]+thick,r]
    for l,r in parts:block(wallbox(l,r))
    for d in ds:
        c=d['center'][axis];fw=d['frame_width'];u,z=c-d['width']/2,c+d['width']/2
        if fw:
            block(wallbox(u,u+fw));block(wallbox(z-fw,z))
for d in p['openings']:
    if d.get('parking_bbox'):block(d['parking_bbox'])
    elif d['operation'].startswith('hinged'):
        h=d['hinge_point'];v=d['open_vector'];r=d['clear_width_target'];e=[h[0]+r*v[0],h[1]+r*v[1]]
        block([min(h[0],e[0])-20,min(h[1],e[1])-20,max(h[0],e[0])+20,max(h[1],e[1])+20])
for f in furn:
    if f['kind'] not in ['wet_floor','drying_rail'] and f['z']<1800 and f['height']+f['z']>150:block(f['bbox'])
sy=int(np.argmin(abs(Y-8500)));sx=int(np.argmin(abs(X-5900)))
assert not blocked[sy,sx], 'Chosen entry start is blocked'
seen=np.zeros_like(blocked);seen[sy,sx]=True;q=deque([(sy,sx)])
while q:
    y,x=q.popleft()
    for yy,xx in [(y+1,x),(y-1,x),(y,x+1),(y,x-1)]:
        if 0<=yy<len(Y) and 0<=xx<len(X) and not seen[yy,xx] and not blocked[yy,xx]:seen[yy,xx]=True;q.append((yy,xx))
reach={}
for rid,r in rooms.items():
    b=r['bbox'];ix=np.where((X>b[0])&(X<b[2]))[0];iy=np.where((Y>b[1])&(Y<b[3]))[0]
    reach[rid]=bool(seen[np.ix_(iy,ix)].any())
report={'source':str(src),'furniture_outside_rooms':outside,'furniture_3d_bbox_collisions_excluding_intentional_wet_floor':solid_collisions,'hinged_door_arc_furniture_collisions':arc_collisions,'planar_route_body_mm':[600,600],'route_resolution_mm':step,'all_doors_fully_open':True,'reachable_from_genkan':reach,'limits':'Basic-plan geometric check only. Does not validate steps, legal access, wheelchair movement, body postures, window products, structural or code compliance.'}
out=Path(__file__).with_name('plan-audit.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
