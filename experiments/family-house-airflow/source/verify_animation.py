from pathlib import Path
import json, subprocess, hashlib, argparse, sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image,ImageOps,ImageDraw
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--work',required=True);a=p.parse_args()
r,w=Path(a.root),Path(a.work);w.mkdir(parents=True,exist_ok=True)
video=r/'この家の風の流れ_3D-CFD.mp4';preview=r/'preview.webp'
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)],text=True,encoding='utf-8'))
stream=next(q for q in probe['streams']if q['codec_type']=='video')
assert stream['codec_name']=='h264' and stream['pix_fmt']=='yuv420p'
assert int(stream['width'])==1920 and int(stream['height'])==1080
duration=float(probe['format']['duration']);assert abs(duration-20)<.1
decode=subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True,encoding='utf-8')
assert decode.returncode==0 and not decode.stderr
frames=[]
for sec in [0,5,10,13,19.9]:
    dest=w/f'decoded-{sec:g}.png'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(sec),'-i',str(video),'-frames:v','1',str(dest)],check=True)
    frames.append((sec,Image.open(dest).convert('RGB').copy()))
motion=[]
for sec in [2,2.15]:
    dest=w/f'motion-{sec:g}.png'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(sec),'-i',str(video),'-frames:v','1',str(dest)],check=True)
    motion.append(np.array(Image.open(dest).convert('RGB'))[280:900,150:1250])
delta=np.max(np.abs(motion[0].astype(int)-motion[1].astype(int)),axis=2)
pixels=int((delta>30).sum());assert pixels>100,('Insufficient decoded particle motion',pixels)
webp=Image.open(preview);n=webp.n_frames;assert n>=100
assert webp.info.get('loop')==0
for i in range(n):webp.seek(i);webp.load()
contact=Image.new('RGB',(960*2,540*3),'white');draw=ImageDraw.Draw(contact)
for i,(sec,im) in enumerate(frames):
    im.thumbnail((960,540));contact.paste(im,((i%2)*960,(i//2)*540))
contact.save(w/'decoded-contact-sheet.png')
result={'status':'pass','video':{'path':str(video),'duration_s':duration,'codec':stream['codec_name'],'pixel_format':stream['pix_fmt'],'resolution':[int(stream['width']),int(stream['height'])],'frames':int(stream['nb_frames']),'all_frames_decoded':True,'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest()},'preview':{'path':str(preview),'frames':n,'loop':0,'all_frames_decoded':True,'bytes':preview.stat().st_size},'motion':{'sample_seconds':[2,2.15],'pixels_changed_gt30':pixels,'roi':[150,280,1250,900]},'sampled_video_seconds':[q[0]for q in frames],'visual_review':'Parent/renderer must separately inspect decoded-contact-sheet.png; automatic decode does not establish readability or CFD correctness'}
(r/'animation-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
