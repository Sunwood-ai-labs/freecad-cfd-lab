"""Compose the family-house design dossier from the shared, frozen design JSON."""
from pathlib import Path
import json
import math
from PIL import Image, ImageChops
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'experiments'/'family-house'
WORK=ROOT/'work'/'family-house-sheets'
SOURCE=ROOT/'experiments'/'family-house'/'house-design.json'
PDF=OUT/'4人家族の平屋_基本設計案.pdf'
DATA=json.loads(SOURCE.read_text(encoding='utf-8-sig'))
OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('JP',r'C:\Windows\Fonts\YuGothM.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('JP-B',r'C:\Windows\Fonts\YuGothB.ttc',subfontIndex=0))
W,H=landscape(A3)
MM=72/25.4
M=40
BG=HexColor('#f5f8fb');INK=HexColor('#17344c');TEXT=HexColor('#2d4357');MUTED=HexColor('#607689');LINE=HexColor('#d8e3eb');TEAL=HexColor('#087d94')

def text(c,s,x,y,size=13,color=TEXT,bold=False):
    c.setFont('JP-B' if bold else 'JP',size);c.setFillColor(color);c.drawString(x,y,str(s))

def lines(s,width,size=13,bold=False):
    result=[];line='';f='JP-B' if bold else 'JP'
    for char in str(s):
        if char=='\n':result.append(line);line='';continue
        if line and pdfmetrics.stringWidth(line+char,f,size)>width:result.append(line);line=char
        else:line+=char
    if line:result.append(line)
    return result

def para(c,s,x,y,width,size=13,leading=21,color=TEXT,bold=False):
    for line in lines(s,width,size,bold):text(c,line,x,y,size,color,bold);y-=leading
    return y

def base(c,n,title,sub):
    c.setFillColor(BG);c.rect(0,0,W,H,stroke=0,fill=1)
    text(c,'FAMILY HOUSE  |  大人2人＋子ども2人の平屋',M,H-29,10,MUTED,True)
    text(c,title,M,H-77,29,INK,True)
    para(c,sub,M,H-106,W-2*M,13,20,MUTED)
    c.setStrokeColor(LINE);c.line(M,32,W-M,32)
    text(c,'基本設計案・建築確認／施工用図面ではありません。法規・構造・設備・製品実寸は建設地確定後に再確認。',M,16,9,MUTED)
    text(c,f'{n:02d} / 07',W-M-58,16,9,MUTED,True)

def card(c,x,y,w,h,title,body,size=13):
    c.setFillColor(HexColor('#ffffff'));c.setStrokeColor(LINE);c.roundRect(x,y,w,h,8,stroke=1,fill=1)
    text(c,title,x+17,y+h-29,15,TEAL,True)
    para(c,body,x+17,y+h-55,w-34,size,21)

def resolve_image(candidates,required=False):
    for n in candidates:
        p=OUT/n
        if p.exists():return p
    if required:raise FileNotFoundError('Required model image not ready: '+', '.join(candidates))
    return None

def image_box(c,p,x,y,w,h,label=None):
    c.setFillColor(HexColor('#ffffff'));c.setStrokeColor(LINE);c.roundRect(x,y,w,h,8,fill=1,stroke=1)
    if p:
        with Image.open(p) as original:
            im=original.convert('RGB')
        if p.name not in ['家具入り平面図.png','生活動線図.png']:
            background=Image.new('RGB',im.size,im.getpixel((0,0)))
            mask=ImageChops.difference(im,background).convert('L').point(lambda x:255 if x>13 else 0)
            bounds=mask.getbbox()
            if bounds:
                pad=34
                im=im.crop((max(0,bounds[0]-pad),max(0,bounds[1]-pad),min(im.width,bounds[2]+pad),min(im.height,bounds[3]+pad)))
        iw,ih=im.size
        scale=min((w-12)/iw,(h-12-(22 if label else 0))/ih);dw,dh=iw*scale,ih*scale
        yy=y+(h-dh)/2+(11 if label else 0)
        c.drawImage(ImageReader(im),x+(w-dw)/2,yy,width=dw,height=dh,mask='auto')
    if label:text(c,label,x+12,y+12,11,MUTED)

def bbox(o):return o.get('bbox') or o.get('bounds') or o.get('rect')
def name(o):return o.get('name_ja') or o.get('label') or o.get('name') or o.get('id')
def value(o,k,default=None):return o.get(k+'_mm',o.get(k,default))
def room_area(r):
    b=bbox(r);return (b[2]-b[0])*(b[3]-b[1])/1e6

def table(c,headers,rows,x,y,widths,row_h=26,size=11.5):
    total=sum(widths);c.setFillColor(HexColor('#e4eef5'));c.rect(x,y-row_h,total,row_h,stroke=0,fill=1)
    xx=x
    for h,w in zip(headers,widths):text(c,h,xx+9,y-row_h+8,size,INK,True);xx+=w
    y-=row_h
    for idx,row in enumerate(rows):
        c.setFillColor(HexColor('#ffffff' if idx%2==0 else '#f0f5f8'));c.rect(x,y-row_h,total,row_h,fill=1,stroke=0)
        xx=x
        for cell,w in zip(row,widths):
            for j,line in enumerate(lines(str(cell),w-18,size)[:2]):text(c,line,xx+9,y-row_h+8-j*(size+2),size,TEXT)
            xx+=w
        y-=row_h
    return y

plan=OUT/'家具入り平面図.png'
if not plan.exists():raise FileNotFoundError(plan)
cutaway=resolve_image(['cutaway.png','roof-off.png','furniture-cutaway.png','interior-isometric.png','model-cutaway.png'],required=True)
exterior=resolve_image(['exterior.png','roof-on.png','exterior-isometric.png','model-exterior.png'],required=True)
rooms=DATA.get('rooms',[]);opens=DATA.get('openings',[])
c=canvas.Canvas(str(PDF),pagesize=(W,H),pageCompression=1)
c.setTitle('4人家族の平屋 3LDK - 基本設計案')
c.setAuthor('Codex - FreeCAD BIM design study')
c.setSubject('家具・収納・家事動線を具体化した住宅基本設計。法規・構造・施工図は未確定。')

base(c,1,'家族4人が、無理なく暮らす平屋',
     '3LDK・約32坪。食事、勉強、洗濯、身支度、就寝を、部屋の形と家具の実寸に落とし込みました。')
image_box(c,cutaway,M,164,775,548,'家具入り断面俯瞰。屋根・壁上部を省略表示。家具・設備は寸法確認用の参考モデル。')
right=M+795
card(c,right,531,W-M-right,181,'家族の前提','大人2人＋子ども2人\n子ども室は最初から独立した2室。\n主寝室はクイーンベッドを想定。\n生活は1層。玄関には150mmの框を仮設定。')
card(c,right,337,W-M-right,181,'面積の基準','外壁外面の外形：12,100 × 9,100 mm\n外形面積：110.11㎡\n壁芯参考：105.91㎡ / 約32.0坪\n申請用の法的面積算定は未確認です。')
card(c,right,164,W-M-right,160,'使い勝手の軸','洗面と脱衣を分離。\nLDKと各寝室の間に共用ホール。\n家族収納は6㎡（通路を含む）。\n来客用トイレは玄関寄りに配置。')
text(c,'採用案の狙い：収納と通路を削り過ぎず、個室の独立性と家事のしやすさを両立する。',M,117,16,INK,True)
para(c,'敷地は約60坪を想定した検討開始条件です。敷地寸法・接道・建設地が未定のため、駐車台数や南庭、建ぺい率の成立はまだ確定していません。',M,84,W-2*M,12.5,20,MUTED)
c.showPage()

# The source image uses 0.2px/mm, so 0.1mm per source pixel prints at 1:50.
c.setFillColor(HexColor('#ffffff'));c.rect(0,0,W,H,fill=1,stroke=0)
c.drawImage(str(plan),30*MM,27*MM,width=360*MM,height=250*MM,mask='auto')
c.setStrokeColor(LINE);c.line(M,32,W-M,32)
text(c,'家具入り平面図 / A3原寸印刷時 1:50（印刷設定「実際のサイズ」）',M,16,9,MUTED)
text(c,'基本設計案・建築確認／施工用図面ではありません。',W/2-20,16,9,MUTED)
text(c,'02 / 07',W-M-58,16,9,MUTED,True)
c.showPage()

base(c,3,'生活の動線と、通れる寸法',
     '部屋の寸法・面積は内法床（家具・固定収納を含む）。椅子、冷蔵庫、着替え、収納の使用域を考慮します。')
area_rows=[]
for r in rooms:
    b=bbox(r)
    if not b:continue
    area_rows.append([name(r),f'{(b[2]-b[0])/1000:.2f} × {(b[3]-b[1])/1000:.2f}',f'{room_area(r):.2f}'])
table(c,['室名','内法寸法 m','面積 ㎡'],area_rows,M,700,[185,150,85],27,12)
card(c,492,543,310,158,'朝の支度','玄関からトイレへはLDKを通らずにアクセス。\n洗面を脱衣・ランドリーから分け、入浴中も洗面を使える構成です。',13)
card(c,822,543,328,158,'帰宅と就寝','玄関ホール → LDK → 東ホール → 各個室。\n他の寝室を通らず、3室それぞれへ入れます。',13)
card(c,492,369,310,158,'家事と収納','脱衣・洗濯・乾燥・畳む作業は北西へ集約。\n家族収納と個室収納を分け、季節物と日常衣類を整理できます。',13)
card(c,822,369,328,158,'子どもの成長','各室に1000×2000のベッド、1200×600の机、奥行600の収納を想定。\n窓の操作をベッドが塞がない配置へ調整。',13)
clear_rows=[]
priority=['kitchen_work','ldk_route','private_hall','entry_hall','child1_route','washer_use']
qmap={q.get('id'):q for q in DATA.get('clearances',[])}
chosen=[qmap[k] for k in priority if k in qmap]
for q in chosen or DATA.get('clearances',[]):
    amount=q.get('width_mm') or q.get('clear_width_mm') or q.get('measured_mm') or q.get('target_mm') or ''
    clear_rows.append([q.get('name_ja') or q.get('name') or q.get('label') or q.get('id'),str(amount),'建具・取手等の動作域は別確認'])
if not clear_rows:
    clear_rows=[['東ホール','1000','家具のない共用通路'],['玄関ホール','900','建具・枠等は選定後確認'],['キッチン前','1200以上','家族の調理・通行を想定'],['食卓脇の動線','900','家具・椅子使用域を考慮']]
table(c,['部位','目安 mm','確認の位置付け'],clear_rows[:6],492,329,[195,90,373],27,11.5)
para(c,'「部屋の面積」と「棚だけの床面積」は別です。家族収納6㎡には歩く空間も含まれます。扉枠・取手・家電扉・製品ごとの必要離隔は、実寸選定後に再確認します。',M,119,W-2*M,12.3,20,MUTED)
c.showPage()

base(c,4,'朝・家事・来客の動き方',
     '歩き方の例を色分けしました。寝室の通り抜けを避け、洗面と脱衣を分け、来客トイレを玄関側にまとめています。')
image_box(c,OUT/'生活動線図.png',M,62,W-2*M,H-185)
c.showPage()

base(c,5,'窓・扉の計画と、採光・換気の考え方',
     '窓の面積だけで法適合を判定せず、建設地と隣地条件を合わせて確認。高窓は家具図で破線表示し、立面・建具表でも確認します。')
windows=[];doors=[]
for o in opens:
    kind=str(o.get('type') or o.get('kind') or '').lower();w=value(o,'width',0);h=value(o,'height',0)
    if 'window' in kind:
        windows.append([o.get('id',''),o.get('name_ja') or o.get('name') or o.get('room',''),f'{w:g}×{h:g}',str(value(o,'sill',0)),f'{w*h/1e6:.2f}'])
    else:
        doors.append([o.get('id',''),o.get('name_ja') or o.get('name') or o.get('room',''),f'{w:g}',str(o.get('clear_width_target',value(o,'clear_width',max(0,w-100))))])
table(c,['ID','窓の位置','幅×高さ mm','腰高 mm','粗面積㎡'],windows,M,700,[50,185,145,75,85],29,11.8)
table(c,['ID','扉の位置','開口 mm','有効目標 mm'],doors,622,700,[60,240,100,130],29,11.6)
card(c,M,151,350,149,'採光','居室には外部に面する窓を計画。\n表示は粗開口寸法です。ガラス面積や採光有効面積とは異なります。\n隣地距離・軒・補正係数は未検証。',12.4)
card(c,425,151,350,149,'換気','24時間換気と台所・浴室排気の計画が必要です。\n窓配置だけで換気性能は保証しません。\n機器容量、給排気位置、圧力損失は今後計算。',12.4)
card(c,810,151,340,149,'開口の構造・防火','南の大きな開口とLDKの無柱想定は、耐力壁・梁・接合部の検討が必要。\n防火地域、延焼、建具性能も未確認。',12.4)
para(c,'扉の有効幅は設計目標で、取手・可動部を含む製品の実有効寸法は未確認です。窓の実開放幅・採光有効面積も未算定。参考：国土交通省の採光・換気資料。',M,108,W-2*M,11.5,18,MUTED)
c.showPage()

base(c,6,'外観と高さの参考',
     '窓・扉の位置と屋根の形をBIMモデルで確認します。基礎・構造材・屋根の納まりを確定した施工図ではありません。')
image_box(c,exterior,M,370,680,330,'屋根付き外観。モデルの参考ボリューム。')
elevations=[('south-elevation.png','南面'),('north-elevation.png','北面'),('east-elevation.png','東面'),('west-elevation.png','西面')]
available=[(resolve_image([n]),label) for n,label in elevations]
available=[v for v in available if v[0]]
if len(available)>=4:
    for i,(img,label) in enumerate(available):
        xx=M+(i%2)*355;yy=81+(1-i//2)*136
        image_box(c,img,xx,yy,340,128,label)
else:
    image_box(c,cutaway,M,81,680,270,'屋根なしの家具配置・室内確認')
card(c,754,477,396,223,'高さ・屋根は設計検討用','想定GL=0 / 仕上床FF=+450 mm\n居室天井高2400 / 壁高2700 mm\n玄関土間+300 / 框150 / 土間天井高2550 mm\n寄棟屋根25°・軒450 mmを参考設定。\nポーチ・段差・敷地勾配は配置と合わせて検討。',13)
card(c,754,236,396,223,'次に寸法を詰める部分','敷地境界からの離れと軒の越境。\n日射・日影・隣家の窓との関係。\n雨樋・軒天・防水・屋根通気。\n室外機・給湯器・点検口の位置。\n柱・梁・基礎・耐力壁・接合部。',13)
text(c,'図面とモデルは同じ部屋・壁・開口データを使用。現地条件による再設計を前提にしています。',M,51,11.8,MUTED)
c.showPage()

base(c,7,'実際に建てる前に、確定すること',
     'この案で生活の形を共有し、敷地・法規・構造・設備の専門設計へ引き継ぐための確認項目です。')
checklist=[
('敷地・配置','建設地、敷地測量、接道、方位、高低差、用途地域、建ぺい率・容積率、斜線・高さ、防火、隣地の状況。駐車・南庭はこれらを確認してから配置。'),
('構造・地盤','地盤調査、基礎、積雪・地震・風、屋根荷重、LDKの架構、南面開口を含む耐力壁、柱・梁・接合部の設計。'),
('断熱・省エネ','地域区分、断熱層・開口性能、結露、日射取得と遮蔽、一次エネルギー計算、適合確認。性能等級やUA値・BEIは未計算。'),
('水回り・空調・換気','給排水・勾配・点検、台所/浴室排気、24h換気の給排気と容量・ダクト、エアコン計画、機器のサービス空間。'),
('製品・収納・暮らし','ユニットバス設置寸法、家電の扉/引出し、戸当たり、玄関庇・雨よけ、ベビーカーや季節家電、将来の介助、コンセント・照明・通信位置。'),
('確認済み／未確認の境界','間取り・家具・アクセス・面積を幾何上で検討。実住宅の安全/法適合/耐久/省エネ/採光換気性能を認証したものではありません。この新間取りのCFD解析も未実施。'),
]
yy=701
for i,(head,body) in enumerate(checklist):
    h=81 if i<5 else 94
    card(c,M,yy-h,W-2*M,h,head,body,12.2)
    yy-=h+10
text(c,'参考一次資料',M,91,11,TEAL,True)
text(c,'国土交通省 省エネ基準適合義務化 https://www.mlit.go.jp/shoene-jutaku/index.html',M,72,10,MUTED)
text(c,'国土交通省 換気 https://www.mlit.go.jp/jutakukentiku/build/jutakukentiku_house_fr_000108.html',M,54,10,MUTED)
c.showPage();c.save()
reader=PdfReader(PDF);assert len(reader.pages)==7
for i,page in enumerate(reader.pages):
    value_text=page.extract_text();assert len(value_text)>50,(i,len(value_text))
report={'pdf':str(PDF),'pages':7,'bytes':PDF.stat().st_size,'source':str(SOURCE),'font':'Embedded Yu Gothic Medium/Bold','text_extraction':'pass','scope':'basic design only; not permit/construction documents'}
(WORK/'pdf-build-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
