from pathlib import Path
import json
import subprocess
from PIL import Image, ImageChops

root=Path(__file__).resolve().parent.parent
work=root/'replay'
qa=work/'qa'
qa.mkdir(exist_ok=True)
movie=root/'窓配置と風通し比較.mp4'
webp=root/'preview.webp'
probe=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,codec_name,pix_fmt,r_frame_rate,nb_frames:format=duration,size','-of','json',str(movie)],capture_output=True,text=True,check=True)
info=json.loads(probe.stdout)
stream=info['streams'][0]
assert (stream['width'],stream['height'])==(1600,1000)
assert stream['codec_name']=='h264' and stream['pix_fmt']=='yuv420p'
assert stream['r_frame_rate']=='24/1'
assert int(stream['nb_frames'])==288
assert abs(float(info['format']['duration'])-12)<.05
decode=subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-map','0:v:0','-f','null','-'],capture_output=True,check=True)
assert decode.returncode==0
for label,index in [('first',0),('middle',144),('last',287)]:
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(movie),'-vf',f'select=eq(n\\,{index})','-frames:v','1',str(qa/f'{label}.png')],capture_output=True,check=True)

def changed(a,b):
    with Image.open(a) as im_a,Image.open(b) as im_b:
        diff=ImageChops.difference(im_a.convert('RGB'),im_b.convert('RGB')).convert('L')
        mask=diff.point(lambda value:255 if value>12 else 0)
        return mask.histogram()[255]

raw_change=changed(work/'frames'/'frame-0000.png',work/'frames'/'frame-0144.png')
decoded_change=changed(qa/'first.png',qa/'middle.png')
assert raw_change>1000 and decoded_change>1000
with Image.open(webp) as im:
    webp_frames=im.n_frames
    assert webp_frames==120
    assert im.size==(960,600)
    for i in range(webp_frames):
        im.seek(i)
        im.load()
    webp_loop=im.info.get('loop')
report={'status':'pass','mp4':info,'full_mp4_decode_exit_code':0,
        'webp_frames':webp_frames,'webp_size':[960,600],'webp_loop':webp_loop,
        'webp_all_frames_decoded':True,
        'source_first_middle_changed_pixels_above_12':raw_change,
        'decoded_first_middle_changed_pixels_above_12':decoded_change,
        'qa_decoded_frames':[str(qa/f'{s}.png') for s in ['first','middle','last']],
        'particle_time_scale':'Common x3 physical IntegrationTime; not equalized path durations',
        'caveat':'Steady 2D flow visualization, not a transient CFD simulation or physical-house validation'}
(root/'animation-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
