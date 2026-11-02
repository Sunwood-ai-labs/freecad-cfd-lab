const fs=require('node:fs');
const path=require('node:path');
const out=process.argv[2]?path.resolve(process.argv[2]):[path.resolve(__dirname,'..'),path.resolve(__dirname,'../../outputs/Family-House-Airflow')].find(p=>fs.existsSync(path.join(p,'setup.json')));
if(!out) throw new Error('Pass the Family-House-Airflow output folder as the first argument.');
const d=JSON.parse(fs.readFileSync(path.join(out,'source-design.json'),'utf8'));
const a=JSON.parse(fs.readFileSync(path.join(out,'setup.json'),'utf8'));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
let parts=[];
const txt=(x,y,s,n=24,c='#193447',w=400,anchor='start')=>parts.push(`<text x="${x}" y="${y}" font-size="${n}" fill="${c}" font-weight="${w}" text-anchor="${anchor}">${esc(s)}</text>`);
const rect=(x,y,w,h,fill,stroke='none',sw=0,r=0)=>parts.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`);
const line=(x1,y1,x2,y2,c='#334f60',sw=4,extra='')=>parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${sw}" ${extra}/>`);
const scale=67,x0=89,y0=865;
const xy=(x,y)=>[x0+x/1000*scale,y0-y/1000*scale];
const planRect=(bb,fill,stroke='none',sw=0)=>{let p=xy(bb[0],bb[3]),q=xy(bb[2],bb[1]);rect(p[0],p[1],q[0]-p[0],q[1]-p[1],fill,stroke,sw);};
parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000"><defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#edf5f6"/><stop offset="1" stop-color="#f3f4f0"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#009caa"/></marker></defs><g font-family="Yu Gothic, Meiryo, sans-serif">`);
rect(0,0,1600,1000,'url(#bg)');
txt(42,65,'この平屋を、南風 2 m/s で解析',43,'#193447',700);
txt(44,112,'設計した3LDKの窓・間仕切り・家具をもとにした3Dモデル',25,'#607585');
rect(36,152,924,788,'#ffffff','none',0,22);
txt(65,196,'窓と室内ドアの開閉条件',27,'#193447',700);
txt(899,226,'北 ↑',23,'#009caa',700,'end');
for(const r of d.rooms) planRect(r.bbox,'#eff4f4');
for(const f of a.furniture){let b=f.bbox_m;planRect([b[0]*1000,b[1]*1000,b[3]*1000,b[4]*1000],'#d9ded9');}
for(const w of d.walls){let p=xy(...w.start),q=xy(...w.end);line(p[0],p[1],q[0],q[1],'#344e5c',w.thickness/1000*scale,'stroke-linecap="square"');}
for(const o of a.apertures){if(o.kind==='window')continue;let b=o.aperture_bbox_m;planRect([b[0]*1000,b[1]*1000,b[3]*1000,b[4]*1000],'#eff4f4');}
for(const o of d.openings.filter(o=>o.kind==='window')){
 let cx=o.center[0],cy=o.center[1],h=200;
 let full=o.axis==='x'?[cx-o.width/2,cy-h/2,cx+o.width/2,cy+h/2]:[cx-h/2,cy-o.width/2,cx+h/2,cy+o.width/2];
 planRect(full,'#9aafb4','#627b82',1);
 let z=a.apertures.find(p=>p.id===o.id).aperture_bbox_m;
 planRect([z[0]*1000,z[1]*1000,z[3]*1000,z[4]*1000],'#ffffff','#009caa',2.3);
}
const short={master:'主寝室',child1:'子ども室1',child2:'子ども室2',entry_hall:'ホール',private_hall:'個室ホール',entry:'玄関',fcl:'家族収納',wc:'WC',bath:'浴室',laundry:'ランドリー',wash:'洗面'};
for(const r of d.rooms){let p=xy((r.bbox[0]+r.bbox[2])/2,(r.bbox[1]+r.bbox[3])/2);let s=short[r.id]||r.name;txt(p[0],p[1]+7,s,r.id==='ldk'?26:18,'#193447',700,'middle');}
txt(...xy(5900,9550),'玄関ドア閉鎖',17,'#607585',400,'middle');
for(const x of [1650,4800,10550]){let p=xy(x,0);line(p[0],922,p[0],888,'#009caa',4);parts.push(`<path d="M${p[0]-8} 891 L${p[0]} 877 L${p[0]+8} 891 Z" fill="#009caa"/>`);}
txt(485,918,'南からの風',21,'#009caa',700,'middle');
rect(988,152,576,264,'#193447','none',0,22);
txt(1018,200,'今回の条件',26,'#ffffff',700);
txt(1018,246,'外の風：南 → 北  2 m/s',29,'#65d7d7',700);
txt(1018,292,'室内ドア：全開の開口近似',25,'#ffffff');
txt(1018,336,'玄関：閉鎖 ／ 温度差なし',25,'#ffffff');
txt(1018,382,'隣家・植栽・網戸は省略',23,'#c6d9df');
rect(988,434,576,234,'#ffffff','none',0,22);
txt(1018,479,'引違い窓 7枚',25,'#193447',700);
rect(1020,505,225,54,'#ffffff','#009caa',3);
rect(1245,505,225,54,'#b9c8cc','#688088',2);
txt(1132,594,'開いている半分',21,'#009caa',700,'middle');
txt(1357,594,'閉じた半分',21,'#607585',400,'middle');
txt(1018,640,'枠を除いた内幅の半分を開放',22,'#607585');
rect(988,686,576,254,'#ffffff','none',0,22);
txt(1018,731,'浴室・ランドリーの高窓 2枚',25,'#193447',700);
line(1052,774,1052,893,'#b9c8cc',7);
line(1052,774,1136,858,'#009caa',8);
txt(1163,805,'上吊り外倒し窓',23,'#193447',700);
txt(1163,849,'外へ45°開いた板を近似',22,'#607585');
txt(1163,894,'実際の高さで計算',22,'#607585');
txt(42,975,'条件図です。矢印は外部風の指定方向で、計算結果の流線ではありません。',21,'#607585');
parts.push('</g></svg>');
fs.writeFileSync(path.join(out,'解析条件.svg'),parts.join('\n'));
console.log('Wrote condition diagram from R4 + actual setup');
