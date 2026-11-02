from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[3]
def bb(x0,y0,x1,y1):
    return [round(v*1000)+50 for v in (x0,y0,x1,y1)]
rooms=[]
def room(id,name,bbox,kind):
    rooms.append(dict(id=id,name=name,bbox=bbox,kind=kind,area_m2=(bbox[2]-bbox[0])*(bbox[3]-bbox[1])/1e6))
room('ldk','LDK',bb(.15,.15,6.35,5.15),'living')
room('master','主寝室',bb(8.05,.15,11.85,4.15),'bedroom')
room('child1','子ども室1',bb(6.45,5.35,9.1,8.85),'bedroom')
room('child2','子ども室2',bb(9.2,5.35,11.85,8.85),'bedroom')
room('fcl','家族収納',bb(6.45,.15,7.95,4.15),'storage')
room('private_hall','個室ホール',bb(6.45,4.25,11.85,5.25),'circulation')
room('bath','浴室・1616設置枠',bb(.15,6.95,2.05,8.85),'bath')
room('wash','独立洗面',bb(.15,5.25,2.05,6.85),'wash')
room('laundry','脱衣・ランドリー',bb(2.15,5.25,4.25,8.85),'laundry')
room('wc','トイレ',bb(4.35,5.25,5.35,7.05),'wc')
room('entry_hall','玄関ホール',bb(5.45,5.25,6.35,7.05),'circulation')
room('entry','玄関・靴収納',bb(4.35,7.15,6.35,8.85),'entry')

walls=[]
def wall(id,start,end,thickness=100,external=False):
    walls.append(dict(id=id,start=start,end=end,thickness=thickness,height=2700,external=external))
wall('ext_south',[100,100],[12000,100],200,True)
wall('ext_east',[12000,100],[12000,9000],200,True)
wall('ext_north',[12000,9000],[100,9000],200,True)
wall('ext_west',[100,9000],[100,100],200,True)
wall('spine',[6450,100],[6450,9000])
wall('service_south',[100,5250],[6450,5250])
wall('bath_wash',[100,6950],[2150,6950])
wall('wet_split',[2150,5250],[2150,9000])
wall('laundry_east',[4350,5250],[4350,9000])
wall('wc_hall',[5450,5250],[5450,7150])
wall('entry_south',[4350,7150],[6450,7150])
wall('private_south',[6450,4250],[12000,4250])
wall('private_north',[6450,5350],[12000,5350])
wall('master_fcl',[8050,100],[8050,4250])
wall('children_split',[9200,5350],[9200,9000])

openings=[]
def opening(id,name,host,center,width,height,sill,kind,rooms,operation='fixed',hinge=None,parking=None):
    frame=0 if kind=='passage' else 50
    openings.append(dict(id=id,name=name,host=host,center=center,width=width,height=height,sill=sill,kind=kind,
        frame_width=frame,clear_width_target=width-2*frame,connects=rooms,operation=operation,hinge=hinge,parking_bbox=parking))
opening('D01','玄関ドア','ext_north',[5900,9000],1000,2200,-150,'door',['outside','entry'],'hinged_out','east')
opening('D02','玄関框150・ホール開口','entry_south',[5950,7150],900,2350,-150,'passage',['entry','entry_hall'],'open')
opening('D03','玄関ホール→LDK','service_south',[5950,5250],900,2100,0,'door',['entry_hall','ldk'],'hinged_in','west')
opening('D04','LDK→独立洗面','service_south',[1550,5250],900,2100,0,'door',['ldk','wash'],'sliding_outset',parking=[200,5150,1100,5190])
opening('D05','洗面→脱衣','wet_split',[2150,6350],900,2100,0,'door',['wash','laundry'],'hinged_in','south')
opening('D06','脱衣→浴室','wet_split',[2150,7525],850,2000,0,'door',['laundry','bath'],'sliding_outset',parking=[2210,7950,2250,8800])
opening('D07','ホール→トイレ','wc_hall',[5450,5800],850,2100,0,'door',['entry_hall','wc'],'sliding_outset',parking=[5510,6225,5550,7075])
opening('D08','LDK→個室ホール','spine',[6450,4800],900,2100,0,'door',['ldk','private_hall'],'sliding_outset',parking=[6350,3450,6390,4350])
opening('D09','ホール→家族収納','private_south',[7575,4250],850,2100,0,'door',['private_hall','fcl'],'hinged_in','east')
opening('D10','ホール→主寝室','private_south',[8650,4250],900,2100,0,'door',['private_hall','master'],'hinged_in','west')
opening('D11','ホール→子ども室1','private_north',[8650,5350],900,2100,0,'door',['private_hall','child1'],'hinged_in','east')
opening('D12','ホール→子ども室2','private_north',[11400,5350],900,2100,0,'door',['private_hall','child2'],'hinged_in','east')
opening('W01','ダイニング南腰窓','ext_south',[1650,100],2000,1200,900,'window',['ldk','outside'],'sliding')
opening('W02','リビング南掃出窓','ext_south',[4800,100],2400,2100,0,'window',['ldk','outside'],'sliding')
opening('W03','LDK西窓','ext_west',[100,3250],900,900,1200,'window',['ldk','outside'],'sliding')
opening('W04','子ども室1北窓','ext_north',[8300,9000],1400,1300,900,'window',['child1','outside'],'sliding')
opening('W05','子ども室2北窓','ext_north',[11050,9000],1400,1300,900,'window',['child2','outside'],'sliding')
opening('W06','主寝室南窓','ext_south',[10550,100],1800,1200,900,'window',['master','outside'],'sliding')
opening('W07','主寝室東窓','ext_east',[12000,2850],1200,1200,900,'window',['master','outside'],'sliding')
opening('W08','浴室北高窓','ext_north',[1150,9000],600,600,1500,'window',['bath','outside'],'awning')
opening('W09','ランドリー北高窓','ext_north',[3550,9000],900,600,1600,'window',['laundry','outside'],'awning')

furniture=[]
def furn(id,name,room_id,bbox,height,kind,z=0,rotation=0,fixed=False):
    furniture.append(dict(id=id,name=name,room=room_id,bbox=bbox,height=height,z=z,kind=kind,rotation=rotation,fixed=fixed))
furn('kitchen','I型キッチン2550','ldk',bb(2.85,4.5,5.4,5.15),850,'kitchen',fixed=True)
furn('fridge','冷蔵庫750×750','ldk',bb(2.05,4.4,2.8,5.15),1850,'fridge',rotation=180)
furn('table','4人ダイニング1600','ldk',bb(.95,1.6,2.55,2.4),720,'dining_table')
for i,(x,y) in enumerate([(1.1,1.1),(1.85,1.1),(1.1,2.4),(1.85,2.4)],1):
    furn('dining_chair'+str(i),'椅子'+str(i),'ldk',bb(x,y,x+.5,y+.5),800,'chair')
furn('sofa','ソファ2200・東向き','ldk',bb(3.45,.55,4.35,2.75),780,'sofa',rotation=90)
furn('tv','TVボード1800','ldk',bb(5.95,.75,6.35,2.55),500,'tv_unit',rotation=90)
furn('queen','クイーン1600×2000','master',bb(8.95,.15,10.55,2.15),450,'bed',rotation=180)
furn('master_closet','主寝室収納2500','master',bb(9.35,3.55,11.85,4.15),2200,'wardrobe',fixed=True)
furn('fcl_storage','家族収納・片側600','fcl',bb(6.45,.15,7.05,4.15),2200,'wardrobe',fixed=True)
for key,dx in [('child1',0),('child2',2.75)]:
    furn(key+'_bed','ベッド1000×2000',key,bb(6.45+dx,5.35,7.45+dx,7.35),450,'bed')
    furn(key+'_desk','机1200×600',key,bb(6.45+dx,8.25,7.65+dx,8.85),720,'desk')
    furn(key+'_chair','机椅子',key,bb(6.7+dx,7.65,7.2+dx,8.15),800,'chair')
    furn(key+'_closet','個室収納1200×600',key,bb(8.5+dx,6.55,9.1+dx,7.75),2200,'wardrobe',fixed=True)
furn('bath_inner','1616浴室内寸参考','bath',bb(.3,7.1,1.9,8.7),80,'wet_floor',fixed=True)
furn('tub','浴槽参考750×1400','bath',bb(.4,7.2,1.15,8.6),580,'bathtub',fixed=True)
furn('vanity','洗面台900×600','wash',bb(.15,5.6,.75,6.5),850,'vanity',fixed=True)
furn('washer','ドラム洗濯機650×700','laundry',bb(2.3,8.15,2.95,8.85),900,'washer')
furn('dryer','積層乾燥機参考','laundry',bb(2.3,8.15,2.95,8.85),850,'dryer',z=920)
furn('fold_counter','畳み台1600×600','laundry',bb(3.65,6.0,4.25,7.6),850,'counter',fixed=True)
furn('linen','リネン収納2100×500','laundry',bb(2.15,5.25,4.25,5.75),1800,'wardrobe',fixed=True)
furn('drying_rail','補助物干し・可動式','laundry',bb(3.7,6.2,4.2,7.5),40,'drying_rail',z=2050)
furn('toilet','便器参考400×700','wc',bb(4.65,6.3,5.05,7.0),750,'toilet',fixed=True)
furn('wc_basin','WC手洗い250×350','wc',[4400,5350,4650,5700],800,'small_basin',fixed=True)
furn('shoe','壁面靴収納・土間','entry',bb(4.35,7.15,4.7,8.85),2100,'wardrobe',z=-150,fixed=True)
furn('stroller','ベビーカー置場600×900','entry',bb(4.75,7.95,5.35,8.85),1050,'stroller',z=-150)

clearances=[]
def clear(id,label,room_id,bbox,target_mm,kind='design_target'):
    clearances.append(dict(id=id,label=label,room=room_id,bbox=bbox,target_mm=target_mm,kind=kind))
clear('kitchen_work','調理台前1200','ldk',bb(2.85,3.3,5.4,4.5),1200)
clear('fridge_use','冷蔵庫前1200','ldk',bb(2.05,3.2,2.8,4.4),1200)
clear('dining_north','椅子引き600・北','ldk',bb(.95,2.4,2.55,3.0),600,'operational_zone')
clear('dining_south','椅子引き600・南','ldk',bb(.95,1.0,2.55,1.6),600,'operational_zone')
clear('ldk_route','ダイニング横900','ldk',bb(2.55,.55,3.45,2.75),900)
clear('ldk_entry','玄関からLDKへの通路900','ldk',bb(5.45,3.0,6.35,5.15),900)
clear('bed_left','ベッド左900','master',bb(8.05,.15,8.95,2.15),900)
clear('bed_right','ベッド右1300','master',bb(10.55,.15,11.85,2.15),1300)
clear('bed_foot','ベッド足元1400','master',bb(8.95,2.15,10.55,3.55),1400)
clear('fcl_aisle','収納前900','fcl',bb(7.05,.15,7.95,4.15),900)
clear('private_hall','ホール1000','private_hall',bb(6.45,4.25,11.85,5.25),1000)
clear('entry_hall','玄関ホール900','entry_hall',bb(5.45,5.25,6.35,7.05),900)
clear('washer_use','洗濯機前1200','laundry',bb(2.3,6.95,2.95,8.15),1200)
clear('vanity_use','洗面台前900','wash',bb(.75,5.6,1.65,6.5),900)
clear('wc_front','便器前1050','wc',bb(4.65,5.25,5.05,6.3),1050)
for key,dx in [('child1',0),('child2',2.75)]:
    clear(key+'_route','中央通路1050',key,bb(7.45+dx,5.35,8.5+dx,7.75),1050)
    clear(key+'_chair','椅子引き800',key,bb(6.65+dx,7.45,7.25+dx,8.25),800,'operational_zone')
    clear(key+'_window','窓の操作床',key,bb(7.7+dx,7.85,8.9+dx,8.85),1000,'operational_zone')

label_positions={'ldk':[3850,3800],'master':[10000,2950],'child1':[8250,8100],'child2':[11000,8100],'fcl':[7550,2350],'private_hall':[10500,4800],'bath':[1600,8250],'wash':[1450,6800],'laundry':[3250,7900],'wc':[4850,5700],'entry_hall':[5950,6750],'entry':[5100,7550]}
for item in rooms: item['label_pos']=label_positions[item['id']]
for item in furniture:
    if item['kind']=='wardrobe':
        item['storage_operation']='オープン棚/ハンガー、または引違い戸を想定。開き扉は未検証。'
    if item['kind']=='wet_floor':
        item['reference_only']=True
        item['note']='1616内寸の範囲を示す面マーカー。80mm段差を設計したものではない。'
room_map={r['id']:r for r in rooms}
wall_map={w['id']:w for w in walls}
for op in openings:
    host=wall_map[op['host']]
    horizontal=host['start'][1]==host['end'][1]
    op['axis']='x' if horizontal else 'y'
    if op['kind']=='window':
        op['frame_inner_span_target']=op.pop('clear_width_target')
        op['operable_clear_width_target']=None
        op['opening_note']='枠内幅は実開放幅ではない。引違い/開き窓の開放寸法と採光有効面積は製品・敷地条件未確定。'
    if op['hinge']:
        cx,cy=op['center']; half=op['clear_width_target']/2
        h=op['hinge']
        op['hinge_point']=[cx+(-half if h=='west' else half),cy] if horizontal else [cx,cy+(-half if h=='south' else half)]
        op['closed_vector']=[1 if h=='west' else -1,0] if horizontal else [0,1 if h=='south' else -1]
        if op['operation']=='hinged_out':
            op['open_vector']=[0,1]
        else:
            target=room_map[op['connects'][1]]['bbox']
            op['open_vector']=[0,1 if (target[1]+target[3])/2>cy else -1] if horizontal else [1 if (target[0]+target[2])/2>cx else -1,0]

for w in walls:
    w['base_level']=300 if w['external'] or w['id'] in ['spine','laundry_east','entry_south'] else 450
    w['top_level']=3150
    w['height']=w['top_level']-w['base_level']
for r in rooms:
    r['floor_level']=300 if r['id']=='entry' else 450
    r['ceiling_level']=2850
    r['clear_height']=r['ceiling_level']-r['floor_level']

design={
 'schema_version':1,'design_revision':'R4-frozen','units':'mm','north':'+Y','origin':'southwest exterior corner','status':'基本設計案・敷地法規構造省エネ未確認',
 'project':{'name':'4人家族の平屋','family':'大人2人＋子ども2人','type':'平屋3LDK','building_site':'未定。約60坪・南庭を仮定、敷地寸法/接道/建設地/予算は未確定','client_choice':'平屋で進める'},
 'building':{'outer_bbox':[0,0,12100,9100],'external_wall_thickness':200,'internal_wall_thickness':100,'wall_height':2700,'wall_top_level':3150,'ceiling_height':2400,'finished_floor_level':450,'genkan_floor_level':300,'genkan_lower_bbox':[4400,7200,6400,8900],'genkan_threshold_bbox':[5400,8900,6400,9100],'genkan_step_at':'D01の敷居は土間300で外部ポーチ300へ連続。D02で土間300から玄関ホール450へ150mm上がる','floor_slab_thickness':200,'roof':{'type':'hip','pitch_degrees':25,'eaves':450,'thickness':120},'exterior_footprint_m2':110.11,'wall_center_reference_area_m2':105.91,'wall_center_reference_tsubo':105.91/3.305785,'area_note':'壁芯による参考面積。申請上の床面積・建築面積算定は未確認。外部ポーチ等を含めていない。'},
 'rooms':rooms,'walls':walls,'openings':openings,'furniture':furniture,'clearances':clearances,
 'external_reference':[{'id':'porch','name':'玄関ポーチ参考','bbox':[5000,9100,6800,10600],'top_level':300,'thickness':150},{'id':'porch_step','name':'外部1段参考','bbox':[5000,10600,6800,11050],'top_level':150,'thickness':150}],
 'circulation':{'outside_to_private':['outside','entry','entry_hall','ldk','private_hall','child1/child2/master/fcl'],'laundry':['ldk','wash','laundry','bath'],'guest_wc':['outside','entry','entry_hall','wc'],'notes':['寝室は共用ホールから個別に入室、他室を通らない','洗面と脱衣は別室、洗面を使いながら浴室/脱衣の扉を閉じられる','洗濯と乾燥・畳みはランドリー内、家族収納への専用回遊動線はない','FCL6m²は通路を含む。棚の床面積と区別する','独立SICではなく壁面靴収納＋土間余白','ベビーカーは参考置場、玄関扉の最終製品動作域要確認']},
 'design_checks':{'room_clear_area_sum_m2':sum(r['area_m2'] for r in rooms),'inner_envelope_area_m2':11.7*8.7,'main_routes_target_mm':[900,1000],'door_clear_widths':'主要室800、玄関900、WC/FCL/浴室750を目標。公称開口・枠・製品実有効幅は別','kitchen_design_basis':'2人使用を想定し通路1200を設計目標。メーカー資料による目安で法定最低値ではない'},
 'unverified':['敷地寸法と接道、建ぺい率・容積率・斜線・隣地・防火・地域条例','地盤・基礎・柱・梁・耐力壁・屋根架構・耐震計算','LDK6.2m無柱想定と南側大開口の構造成立','採光有効面積・自然換気有効面積・24時間換気・日照・CFD','断熱/気密/日射遮蔽・省エネ基準・結露・空調計算','雨仕舞・排水・給排水/電気/ガス/給湯・設備ダクト経路','建具/サッシ/浴室/設備の製品実寸・設置余白・戸当たり・取手突出','玄関土間と外部の段差・外部ポーチ/庭/駐車の敷地上の成立','予算・見積・施工者・確認申請・施工図'],
 'references':[
  {'topic':'キッチンの2人用通路120cm前後の目安','url':'https://www.lixil.co.jp/lineup/s/navi/knowledge/kitchen/'},
  {'topic':'1616は浴室内寸1600×1600の呼称で設置外寸ではない','url':'https://jp.toto.com/reform/library/neue/article26/'},
  {'topic':'2025年4月以降の新築住宅の省エネ基準適合','url':'https://www.mlit.go.jp/shoene-jutaku/index.html'},
  {'topic':'住宅の24時間換気の制度説明','url':'https://www.mlit.go.jp/jutakukentiku/build/jutakukentiku_house_fr_000108.html'},
  {'topic':'住宅採光規定と有効面積の扱い','url':'https://www.mlit.go.jp/jutakukentiku/build/r4kaisei_kijunhou0006.html'}]
}
for target in [ROOT/'experiments/family-house/house-design.json',ROOT/'experiments/family-house/house-design.json']:
 target.write_text(json.dumps(design,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'rooms':len(rooms),'walls':len(walls),'openings':len(openings),'furniture':len(furniture),'area_m2':design['design_checks']['room_clear_area_sum_m2']},ensure_ascii=False))
