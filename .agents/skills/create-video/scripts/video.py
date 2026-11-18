#!/usr/bin/env python3
"""create-video workflow: cached audio/keyframes/render, media validation, reports and site handoff."""
import argparse,contextlib,fcntl,hashlib,html,json,os,re,shutil,subprocess,sys,tarfile,time
from pathlib import Path
SKILL=Path(__file__).resolve().parent.parent
VERSION='2'

def read(p):return json.loads(Path(p).read_text())
def write(p,value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def signature(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def source_hash(root,voice=False):
 return {str(p.relative_to(root)):digest(p) for p in sorted((root/'source').glob('*.py')) if (p.name=='generate_audio.py')==voice}
def load(root):
 c=read(root/'video.json');v=c['video']
 if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',c['slug']):raise ValueError('slug must use lower-case letters, numbers and hyphens')
 if (v['width'],v['height'],v['fps'],v['duration'],v['frames'])!=(1920,1080,30,60,1800):raise ValueError('Bundled drawing templates currently support 1920x1080 / 30fps / 60s; adapt template and validator for other formats rather than silently changing a request')
 scenes=c['scenes']
 if len(scenes)!=6 or scenes[0]['start']!=0 or scenes[-1]['end']!=v['duration'] or any(a['end']!=b['start'] for a,b in zip(scenes,scenes[1:])):raise ValueError('Timeline must contain six contiguous scenes covering the complete film')
 if any(s['end']<=s['start'] or not s['narration'].strip() for s in scenes):raise ValueError('Empty scene or narration')
 return c

def runtime(c,root):
 candidates=[c.get('runtime',{}).get('python'),os.getenv('CREATE_VIDEO_PYTHON'),str(root/'.venv/bin/python'),'/workspace/work/venv/bin/python',sys.executable]
 for value in dict.fromkeys(x for x in candidates if x):
  if Path(value).is_file() and subprocess.run([value,'-c','import skia,numpy,PIL'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return value
 raise RuntimeError('No cached Python with skia/numpy/Pillow found. Set CREATE_VIDEO_PYTHON or video.json runtime.python; install only missing dependencies.')
def model(c):
 for value in [os.getenv('KOKORO_MODEL_DIR'),c.get('runtime',{}).get('model'),'/workspace/work/models/kokoro-int8-multi-lang-v1_0']:
  if value and all((Path(value)/n).is_file() for n in ['model.int8.onnx','voices.bin','tokens.txt']):return value
 raise RuntimeError('Cached Kokoro model not found. Set KOKORO_MODEL_DIR; no automatic network download is attempted.')
def film(root,c):return root/'output'/f"{c['slug']}-{c['video']['duration']}s.mp4"
def visual(root,c):return {'source':source_hash(root),'scenes':c['scenes'],'video':c['video'],'title':c['title'],'onscreen_text':c.get('onscreen_text',[])}

@contextlib.contextmanager
def lock(root):
 (root/'work').mkdir(exist_ok=True)
 with (root/'work/pipeline.lock').open('w') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('Another pipeline command owns this project; do not overlap edits/builds to the same output')
  yield

def stage(root,name,inputs,outputs,action):
 statepath=root/'work/pipeline.json';state=read(statepath) if statepath.exists() else {'version':VERSION,'stages':{}};key=signature({'version':VERSION,'inputs':inputs});previous=state['stages'].get(name,{})
 current={str(p.relative_to(root)):digest(p) for p in outputs if p.is_file()}
 if previous.get('key')==key and len(current)==len(outputs) and current==previous.get('outputs'):
  print(f'CACHE {name}',flush=True);return False
 begin=time.monotonic();action()
 if any(not p.is_file() for p in outputs):raise RuntimeError('Stage did not produce all required files: '+name)
 state['stages'][name]={'key':key,'wall_seconds':time.monotonic()-begin,'finished_epoch':time.time(),'outputs':{str(p.relative_to(root)):digest(p) for p in outputs}}
 write(statepath,state);print(f'DONE {name} {state["stages"][name]["wall_seconds"]:.2f}s',flush=True);return True

def command(root,name,args,env=None):
 log=root/'work'/f'{name}.log'
 with log.open('w') as f:r=subprocess.run(args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(f'{name} failed; {log}\n'+log.read_text()[-3000:])
def audio(root,c):
 requested=os.getenv('KOKORO_MODEL_DIR') or c.get('runtime',{}).get('model') or '/workspace/work/models/kokoro-int8-multi-lang-v1_0'
 inputs={'narration':[(s['start'],s['end'],s['narration']) for s in c['scenes']],'voice':c['voice'],'source':source_hash(root,True),'model':str(requested)}
 def generate():
  py=runtime(c,root);mp=model(c);env=os.environ.copy();env['KOKORO_MODEL_DIR']=mp
  command(root,'audio',[py,'source/generate_audio.py'],env)
 return stage(root,'audio',inputs,[root/'assets/soundtrack.m4a',root/'assets/voice-timing.json'],generate)
def keyframe_inputs(root,c):
 return {**visual(root,c),'voice_timing':digest(root/'assets/voice-timing.json'),'runtime':digest(SKILL/'scripts/render_runtime.py')}
def keyframes(root,c):
 if not (root/'assets/voice-timing.json').is_file():raise RuntimeError('Run audio first, or import a measured existing soundtrack/timing')
 inputs=keyframe_inputs(root,c)
 return stage(root,'keyframes',inputs,[root/'work/keyframes.jpg',root/'output/poster.jpg'],lambda:command(root,'keyframes',[runtime(c,root),str(SKILL/'scripts/render_runtime.py'),'keyframes','--project',str(root)]))
def review(root,c,note):
 if not note.strip():raise ValueError('Record what was visually/scientifically checked, not an empty approval')
 contact=root/'work/keyframes.jpg'
 if not contact.exists():raise ValueError('Generate and inspect keyframes first')
 state=read(root/'work/pipeline.json')
 if state.get('stages',{}).get('keyframes',{}).get('key')!=signature({'version':VERSION,'inputs':keyframe_inputs(root,c)}):raise ValueError('Keyframes are stale; regenerate them before recording review')
 if c.get('template')=='generic' and digest(root/'source/film.py')==digest(SKILL/'templates/dark-matter/source/film.py'):raise ValueError('A new topic still uses the unchanged reference science; adapt source/film.py before review')
 write(root/'work/review.json',{'visual':signature(visual(root,c)),'contact':digest(contact),'note':note,'epoch':time.time()})
 print('Recorded internal content/keyframe review; no user confirmation is required')
def render(root,c):
 if not (root/'work/keyframes.jpg').is_file():raise RuntimeError('Generate and inspect keyframes before rendering')
 reviewed=read(root/'work/review.json') if (root/'work/review.json').exists() else {}
 if reviewed.get('visual')!=signature(visual(root,c)) or reviewed.get('contact')!=digest(root/'work/keyframes.jpg'):raise RuntimeError('Inspect current keyframes/science, then run review --note. A source/timeline change invalidates an earlier review.')
 inputs={**visual(root,c),'soundtrack':digest(root/'assets/soundtrack.m4a'),'runtime':digest(SKILL/'scripts/render_runtime.py')}
 return stage(root,'render',inputs,[film(root,c),root/'output/render-results.json'],lambda:command(root,'render',[runtime(c,root),str(SKILL/'scripts/render_runtime.py'),'render','--project',str(root)]))
def verify(root,c,path=None):
 video=path or film(root,c);v=c['video'];inputs={'video':digest(video),'spec':v,'validator':digest(Path(__file__))}
 def execute():
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]));streams=probe['streams'];s=next(s for s in streams if s['codec_type']=='video');a=next((s for s in streams if s['codec_type']=='audio'),None)
  from fractions import Fraction
  if (s['width'],s['height'],Fraction(s['r_frame_rate']),s['pix_fmt'],s['codec_name'],int(s.get('nb_frames',0)))!=(v['width'],v['height'],Fraction(v['fps']), 'yuv420p','h264',v['frames']):raise RuntimeError('ffprobe video parameters do not match the request')
  if abs(float(probe['format']['duration'])-v['duration'])>1/v['fps'] or a is None:raise RuntimeError('Duration or audio missing')
  hashes=root/'work/decoded.md5';log=root/'work/decode.log'
  with log.open('w') as f:subprocess.run(['ffmpeg','-hide_banner','-loglevel','info','-y','-i',str(video),'-vf','blackdetect=d=0.2:pix_th=0.01:pic_th=0.999','-an','-f','framemd5',str(hashes)],check=True,stdout=f,stderr=f)
  rows=[l for l in hashes.read_text().splitlines() if l and not l.startswith('#')];values=[r.split(',')[-1].strip() for r in rows]
  if len(values)!=v['frames'] or 'black_start' in log.read_text():raise RuntimeError('Unexpected black segment or decoded frame count')
  duplicate=sum(values[i]==values[i-1] for i in range(1,len(values)-v['fps']))
  if duplicate:raise RuntimeError(f'{duplicate} identical adjacent decoded frames before the intentional final hold')
  write(root/'output/ffprobe.json',probe);write(root/'output/validation.json',{'passed':True,'video_sha256':digest(video),'decoded_frames':len(values),'black_segments':0,'duplicate_adjacent_before_final_hold':duplicate,'note':'Decoded byte equality is a diagnostic, not proof that all science animation is correct. Visual review remains required.'})
 return stage(root,'verify',inputs,[root/'output/ffprobe.json',root/'output/validation.json'],execute)

def docs(root,c):
 inputs={'science':c['science'],'title':c['title'],'validation':digest(root/'output/validation.json'),'performance':digest(root/'output/render-results.json')}
 def execute():
  perf=read(root/'output/render-results.json');s=c['science']
  (root/'SCIENCE_NOTES.md').write_text('# '+c['title']+'：科学说明\n\n'+s['summary']+'\n\n## 简化与边界\n\n'+'\n'.join('- '+x for x in s['simplifications'])+'\n\n## 参考\n\n'+'\n'.join('- '+x for x in s['references'])+'\n')
  (root/'ASSET_CREDITS.md').write_text('# 素材与许可\n\n'+'\n'.join('- '+x for x in s['asset_credits'])+'\n\n## 限制\n\n'+'\n'.join('- '+x for x in s['limitations'])+'\n')
  seconds=perf['render_wall_seconds'];report=f"# 实测性能\n\n完整渲染：{seconds:.3f} 秒；平均 {perf['average_fps']:.3f} FPS。\n\n编码：H.264 / yuv420p，{c['video']['preset']}，CRF {c['video']['crf']}，{c['video']['threads']} 线程。\n\n文件 {perf['bytes']} 字节。渲染进程峰值 RSS {perf['renderer_peak_rss_kib']/1024:.1f} MiB；FFmpeg 峰值 RSS {perf['ffmpeg_peak_rss_kib']/1024:.1f} MiB。它们不是同时峰值。\n\n仅帧绘制/编码时间计为渲染，不包括配音、编写、验证或发布。缓存命中不是新的渲染测试。详细阶段记录见 work/pipeline.json，原始测量见 output/render-results.json。\n\n完整解码、媒体参数、黑屏与重复帧检查已执行，见 output/validation.json。字幕分句时间来自实测语音区间的字数分配，非音素级强制对齐。\n"
  if seconds>600:report+='\n超过 600 秒目标。瓶颈需要按 drawing_extract_seconds 与 pipe_wait_seconds 的实测值分析，仍交付完整成片。\n'
  (root/'PERFORMANCE_REPORT.md').write_text(report)
  (root/'README.md').write_text('# '+c['title']+'\n\n运行 create-video 的 video.py。先 audio、keyframes，检查后 review --note，再 run --through docs。页面或文档变更不应重跑音频/渲染。\n\n最终成片：'+str(film(root,c).relative_to(root))+'。\n')
 return stage(root,'docs',inputs,[root/'SCIENCE_NOTES.md',root/'ASSET_CREDITS.md',root/'PERFORMANCE_REPORT.md',root/'README.md'],execute)

def init(args):
 root=args.project.resolve()
 if root.exists() and any(root.iterdir()):raise ValueError('Initialize only a new/empty directory; existing work is never overwritten')
 root.mkdir(parents=True,exist_ok=True);template=args.template
 if template=='auto':
  title=args.title or ''
  template='dark-matter' if any(t in title.lower() for t in ['暗物质','dark matter']) else 'cmb' if any(t in title.lower() for t in ['微波背景','cmb']) else 'generic'
 if template=='generic' and not args.slug:raise ValueError('For a new topic, provide --slug and adapt the closest scene mechanisms; no existing film URL is reused implicitly')
 if template=='generic':
  shutil.copytree(SKILL/'templates/dark-matter/source',root/'source');c=read(SKILL/'templates/dark-matter/video.json');c['science']['limitations']=['新主题尚未适配科学模型；必须修改 source/film.py 和 models.py，不能只改标题。'];c['template']='generic'
 else:shutil.copytree(SKILL/'templates'/template/'source',root/'source');c=read(SKILL/'templates'/template/'video.json')
 c['slug']=args.slug or c['slug'];c['title']=args.title or c['title']
 for folder in ['assets','work','output']:(root/folder).mkdir()
 write(root/'video.json',c);load(root)
 (root/'README.md').write_text('先编辑 video.json 和科学分镜；调用 audio/keyframes 后由助手检查，再 review。该目录只使用通用编码/验收流程，不复制新的引擎。\n')
 print(json.dumps({'project':str(root),'template':template,'next':'edit video.json/science and source/film.py; audio, keyframes, review, run --through docs'},ensure_ascii=False))

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
 i=sub.add_parser('init');i.add_argument('--project',type=Path,required=True);i.add_argument('--template',choices=['auto','dark-matter','cmb','generic'],default='auto');i.add_argument('--title');i.add_argument('--slug')
 for name in ['audio','keyframes','render','verify','docs','run','review','site','package','receipt','next','sync']:
  a=sub.add_parser(name);a.add_argument('--project',type=Path,required=True)
  if name=='run':a.add_argument('--through',choices=['keyframes','verify','docs'],default='keyframes')
  if name=='review':a.add_argument('--note',required=True)
  if name=='verify':a.add_argument('--file',type=Path)
  if name in ['site','package','sync']:a.add_argument('--repo',type=Path,required=True)
  if name=='site':
   a.add_argument('--allow-source-changes',action='store_true',help='Use only for a confirmed feature gap or explicit source/page change')
   a.add_argument('--reason',help='Confirmed feature gap or explicit page/source requirement')
  if name=='sync':a.add_argument('--message',default='Update generated science film')
  if name=='package':a.add_argument('--mode',choices=['stage','final'],required=True)
  if name=='receipt':a.add_argument('--phase',required=True,choices=['site_access','stage_saved','stage_deployed','storage_ready','final_saved','final_deployed'])
 args=p.parse_args()
 if args.cmd=='site' and (not args.allow_source_changes or not (args.reason or '').strip()):
  p.error('Existing sites default to direct upload; see references/direct-upload.md. Source integration requires --allow-source-changes and a nonempty --reason.')
 if args.cmd=='init':return init(args)
 root=args.project.resolve();c=load(root)
 with lock(root):
  if args.cmd=='run':
   audio(root,c);keyframes(root,c)
   if args.through!='keyframes':render(root,c);verify(root,c)
   if args.through=='docs':docs(root,c)
  elif args.cmd=='review':review(root,c,args.note)
  elif args.cmd=='verify':verify(root,c,args.file.resolve() if args.file else None)
  elif args.cmd in ['audio','keyframes','render','docs']:globals()[args.cmd](root,c)
  elif args.cmd=='sync':
   from sync_source import sync
   sync(root,args.repo,json.load(sys.stdin),args.message)
  else:
   from site_workflow import dispatch
   dispatch(args,root,c)
if __name__=='__main__':
 try:main()
 except (ValueError,RuntimeError,subprocess.CalledProcessError) as e:print(str(e),file=sys.stderr);sys.exit(1)
