#!/usr/bin/env python3
"""Shared Skia frame inspection and FFmpeg encoding. Science lives in source/film.py."""
import argparse,json,os,resource,runpy,subprocess,sys,time
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['keyframes','render']);p.add_argument('--project',type=Path,required=True);a=p.parse_args();root=a.project.resolve();cfg=json.loads((root/'video.json').read_text());v=cfg['video']
 import numpy as np
 import skia
 from PIL import Image,ImageFont
 # Validate job text against the actual font before encoding all 1800 frames.
 font=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
 if not font.is_file():raise RuntimeError('Noto CJK font missing; choose/install the final font before rendering')
 face=ImageFont.truetype(str(font),36);missing=face.getmask('\uffff');missing_key=(missing.size,bytes(missing));bad=[]
 text=cfg['title']+''.join(s['title']+s['narration'] for s in cfg['scenes'])+''.join(cfg.get('onscreen_text',[]))
 for char in sorted(set(text)):
  if char.isspace():continue
  mask=face.getmask(char)
  if (mask.size,bytes(mask))==missing_key:bad.append(char)
 if bad:raise RuntimeError('Font is missing these glyphs: '+''.join(bad))
 sys.path.insert(0,str(root/'source'));m=runpy.run_path(str(root/'source/film.py'),run_name='create_video_drawing');frame=m['frame'];w,h,fps=v['width'],v['height'],v['fps']
 if (m['W'],m['H'],m['FPS'])!=(w,h,fps):raise RuntimeError('Template canvas and requested video parameters differ; adapt the drawing template explicitly')
 (root/'output').mkdir(exist_ok=True);(root/'work').mkdir(exist_ok=True)
 def pixels(t):
  arr=frame(t).toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
  if arr.shape!=(h,w,4) or arr.dtype!=np.uint8:raise RuntimeError('Invalid frame shape/type')
  return arr
 if a.mode=='keyframes':
  times=[]
  for s in cfg['scenes']:times.extend([s['start']+.08,(s['start']+s['end'])/2])
  times.append(v['duration']-.5);contact=Image.new('RGB',(1440,405*((len(times)+1)//2)));dest=root/'work/keyframes';dest.mkdir(exist_ok=True)
  for i,t in enumerate(times):
   im=Image.fromarray(pixels(t)).convert('RGB');im.save(dest/f'{i:02d}-{t:05.2f}.jpg');contact.paste(im.resize((720,405)),(i%2*720,i//2*405))
  contact.save(root/'work/keyframes.jpg');Image.fromarray(pixels(min(4,v['duration']/12))).convert('RGB').save(root/'output/poster.jpg');print(json.dumps({'frames':len(times),'contact':str(root/'work/keyframes.jpg')}));return
 out=root/'output'/f"{cfg['slug']}-{v['duration']}s.mp4";partial=out.with_name(out.stem+'.partial.mp4');audio=root/'assets/soundtrack.m4a'
 cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgba','-video_size',f'{w}x{h}','-framerate',str(fps),'-i','pipe:0','-i',str(audio),'-map','0:v','-map','1:a','-t',str(v['duration']),'-c:v','libx264','-preset',v['preset'],'-crf',str(v['crf']),'-pix_fmt','yuv420p','-threads',str(v['threads']),'-c:a','copy','-movflags','+faststart',str(partial)]
 start=time.monotonic();cpu=time.process_time();draw=wait=0;errpath=root/'work/encoder.log'
 with errpath.open('w') as err:
  ff=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=err)
  try:
   for i in range(v['frames']):
    t=time.monotonic();arr=pixels(i/fps);draw+=time.monotonic()-t;t=time.monotonic();ff.stdin.write(arr.tobytes());wait+=time.monotonic()-t
    if i%(fps*6)==0:print(f'{i}/{v["frames"]}',flush=True)
   ff.stdin.close()
   if ff.wait()!=0:raise RuntimeError(errpath.read_text())
  except BaseException:
   if ff.poll() is None:ff.terminate();ff.wait()
   partial.unlink(missing_ok=True);raise
 elapsed=time.monotonic()-start;os.replace(partial,out);own=resource.getrusage(resource.RUSAGE_SELF);child=resource.getrusage(resource.RUSAGE_CHILDREN)
 result={'render_wall_seconds':elapsed,'average_fps':v['frames']/elapsed,'drawing_extract_seconds':draw,'pipe_wait_seconds':wait,'python_cpu_seconds':time.process_time()-cpu,'ffmpeg_cpu_seconds':child.ru_utime+child.ru_stime,'renderer_peak_rss_kib':own.ru_maxrss,'ffmpeg_peak_rss_kib':child.ru_maxrss,'bytes':out.stat().st_size,'video':v,'command':cmd}
 (root/'output/render-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
