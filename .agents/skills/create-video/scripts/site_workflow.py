"""Idempotent page integration, content-addressed media staging and native-tool handoff."""
import contextlib,fcntl,html,json,os,re,shutil,subprocess,tarfile,time
from pathlib import Path
from video import SKILL,read,write,digest,signature,film,stage,command

def git(repo,*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
@contextlib.contextmanager
def repo_lock(repo):
 location=Path(git(repo,'rev-parse','--absolute-git-dir'))/'create-video.lock'
 with location.open('w') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('Another create-video process owns this checkout')
  yield

def page(c,route):
 e=lambda x:html.escape(str(x),quote=True);ref=(SKILL/'templates/shared/page-reference.html').read_text();style=ref[ref.index('<style>'):ref.index('</style>')+8];cards=''.join('<article class="card"><small>'+e(card.get('label',''))+'</small><h3>'+e(card['title'])+'</h3><p>'+e(card['text'])+'</p></article>' for card in c['page']['cards'])
 base=route.rsplit('/',1)[0];slug=c['slug'];description=c['page']['description'] or c['title']+'，完整中文科普动画。'
 return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="'+e(description)+'"><title>'+e(c['title'])+' · 个人笔记</title>'+style+'</head><body><header><nav class="wrap"><a href="/">balance 的手记</a><a href="/science.html">← 科学实验室</a></nav></header><main class="wrap"><div class="hero"><div class="eyebrow">SCIENCE FILM</div><h1>'+e(c['title'])+'</h1><p>'+e(description)+'</p><div class="meta">60 秒 · 1080p · 30 FPS · 中文 AI 男声 · 中文字幕</div></div><div class="film"><video id="film" controls playsinline preload="none" poster="'+base+'/poster.jpg" aria-label="'+e(c['title'])+'"><source src="'+route+'" type="video/mp4">请使用下载链接观看。</video><p class="caption">'+e(c['page'].get('visual_note','科学示意与真实观测需以片内标注和素材说明区分。'))+'</p></div><div class="actions"><a class="button primary" href="'+route+'?download" download="'+slug+'-60s.mp4">下载完整 MP4 ↓</a></div><section><h2>理解这条视频</h2><div class="grid">'+cards+'</div></section><section><div class="sources"><a href="'+base+'/SCIENCE_NOTES.md">科学依据</a><a href="'+base+'/ASSET_CREDITS.md">素材说明</a><a href="'+base+'/PERFORMANCE_REPORT.md">实测性能</a></div></section></main><footer class="wrap">balance 的手记 · 点击播放后加载视频。</footer></body></html>'

def site_signature(root,c):
 return signature({'title':c['title'],'page':c['page'],'video':digest(film(root,c)),'documents':{n:digest(root/n) for n in ['SCIENCE_NOTES.md','ASSET_CREDITS.md','PERFORMANCE_REPORT.md']}})

def keep_history(state,fields,reason):
 old={k:state.pop(k) for k in fields if k in state}
 if old:state.setdefault('history',[]).append({'reason':reason,'epoch':time.time(),'records':old})

def integrate(root,c,repo):
 repo=repo.resolve();validation=read(root/'output/validation.json')
 if validation.get('video_sha256')!=digest(film(root,c)):raise RuntimeError('Run verify on the current video before site integration')
 if c['page'].get('source_download'):raise RuntimeError('This lightweight page template does not upload a source archive. Deliver sources separately, or explicitly extend the durable media registry first.')
 reviewed=read(root/'work/review.json') if (root/'work/review.json').exists() else {}
 from video import visual
 if reviewed.get('visual')!=signature(visual(root,c)):raise RuntimeError('Science/source changed after review; inspect current keyframes before site integration')
 manifest=read(repo/'.openai/hosting.json');registry_path=repo/'source/films/registry.json';reg=read(registry_path) if registry_path.exists() else {'schema':1,'films':[]};old=next((f for f in reg['films'] if f['slug']==c['slug']),None)
 target=repo/'source/films'/c['slug']
 if not old and (repo/'dist/science'/f"{c['slug']}.html").exists():raise RuntimeError('This URL belongs to an existing unregistered page; choose a new slug or migrate it explicitly')
 media=target/'media';media.mkdir(parents=True,exist_ok=True);filename=f"{c['slug']}-60s.mp4";route=f"/science/{c['slug']}-media/{filename}";sha=digest(film(root,c));key='public-assets/static-v1/'+sha+'/'+filename;receipts=read(root/'work/publish.json') if (root/'work/publish.json').exists() else {}
 evidence=receipts.get('storage_ready',{});ready=evidence.get('key')==key and evidence.get('project_id')==manifest['project_id']
 if old and old.get('sha256')==sha and old.get('storage_ready') and old.get('project_id')==manifest['project_id']:ready=True
 entry={'project_id':manifest['project_id'],'slug':c['slug'],'title':c['title'],'route':f"/science/{c['slug']}.html",'asset_route':route,'filename':filename,'sha256':sha,'bytes':film(root,c).stat().st_size,'key':key,'storage_ready':ready}
 for source,name in [(film(root,c),filename),(root/'output/poster.jpg','poster.jpg'),(root/'assets/captions.srt','captions.srt')]+[(root/n,n) for n in ['SCIENCE_NOTES.md','ASSET_CREDITS.md','PERFORMANCE_REPORT.md']]:shutil.copyfile(source,media/name)
 # Retain reproducible science source privately in the source repository.
 source_record=target/'film';source_record.mkdir(exist_ok=True)
 shutil.copytree(root/'source',source_record/'source',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
 write(source_record/'video.json',c)
 (source_record/'assets').mkdir(exist_ok=True)
 for name in ['soundtrack.m4a','voice-timing.json']:
  shutil.copyfile(root/'assets'/name,source_record/'assets'/name)
 (target/'index.html').write_text(page(c,route));reg['films']=[f for f in reg['films'] if f['slug']!=c['slug']]+[entry];write(registry_path,reg)
 builder=repo/'scripts/build-films.mjs';expected=(SKILL/'templates/shared/build-films.mjs').read_text()
 if builder.exists() and not builder.read_text().startswith('// Generated by create-video.'):raise RuntimeError('Existing build-films.mjs is not owned by this tool; merge explicitly')
 builder.write_text(expected);worker=repo/'scripts/build-worker.mjs';text=worker.read_text()
 if "await import('./build-films.mjs');" not in text:
  marker='const assets = {};'
  if marker not in text or 'const mediaSeeds = {};' not in text:raise RuntimeError('Unsupported Worker build layout: use the current Sites skill to adapt storage once')
  handler=(repo/'worker/index.template.js').read_text()
  if not all(x in handler for x in ['FixedLengthStream','asset.chunks','MEDIA_SEED_READY']):raise RuntimeError('Worker lacks the established bounded-memory media seeding handler; adapt it once before installing generic films')
  text=text.replace(marker,"await import('./build-films.mjs');\nconst filmRegistry=JSON.parse(await readFile(path.join(root,'source/films/registry.json'),'utf8')).films;\nconst filmStage=process.env.SITES_FILMS_STAGE;\n"+marker)
  marker='      const bytes = await readFile(full);'
  block='''
      const filmEntry=filmRegistry.find(f=>f.asset_route===rel);
      if(filmEntry){
        const hash=createHash('sha256').update(bytes).digest('hex');
        if(hash!==filmEntry.sha256||bytes.length!==filmEntry.bytes)throw Error('Registered film content changed; regenerate its metadata');
        const meta={key:filmEntry.key,filename:filmEntry.filename,size:filmEntry.bytes,contentType:'video/mp4',r2Only:true};
        if(filmStage!==filmEntry.slug){if(!filmEntry.storage_ready)throw Error('Film storage is unverified; stage once and record MEDIA_SEED_READY first');publicMedia[rel]=meta;continue;}
        mediaSeeds[rel]=meta;const chunks=[];for(let i=0;i<bytes.length;i+=49152)chunks.push(bytes.subarray(i,i+49152).toString('base64'));
        assets[rel]={contentType:'video/mp4',size:bytes.length,chunkSize:49152,chunks};continue;
      }
'''
  if marker not in text:raise RuntimeError('Worker asset insertion point missing')
  text=text.replace(marker,marker+block);worker.write_text(text)
 # Generate the known public files now, before source synchronization, so packaging does not change tracked input files.
 subprocess.run(['node','scripts/build-films.mjs'],cwd=repo,check=True)
 info={'repo':str(repo),'project_id':manifest['project_id'],'site_signature':site_signature(root,c),**entry}
 previous=read(root/'work/site.json') if (root/'work/site.json').exists() else {}
 if previous and (previous.get('key')!=key or previous.get('project_id')!=info['project_id']):
  keep_history(receipts,[k for k in list(receipts) if k!='history'],'media changed; prior IDs retained for audit')
 elif previous and previous.get('site_signature')!=info['site_signature']:
  keep_history(receipts,['final_package','final_saved','final_deployed'],'page/documents changed; reuse verified storage and video')
 write(root/'work/publish.json',receipts);write(root/'work/site.json',info)
 paths=[str(p.relative_to(repo)) for folder in [target,repo/'dist/science'/f"{c['slug']}-media"] for p in folder.rglob('*') if p.is_file()]
 paths+=['source/films/registry.json','scripts/build-films.mjs','scripts/build-worker.mjs','dist/science.html',f"dist/science/{c['slug']}.html"]
 write(root/'work/site-files.json',paths);print(json.dumps({'prepared':info,'next':'sync source, then package --mode '+('final' if ready else 'stage')},ensure_ascii=False))

def package(root,c,repo,mode):
 info=read(root/'work/site.json')
 if Path(info['repo']).resolve()!=repo.resolve():raise RuntimeError('Site metadata belongs to a different checkout')
 sync=read(root/'work/sync.json') if (root/'work/sync.json').exists() else {};head=git(repo,'rev-parse','HEAD')
 if sync.get('head')!=head:raise RuntimeError('Sync this exact source state before packaging')
 if git(repo,'status','--porcelain','--untracked-files=no'):raise RuntimeError('Tracked checkout changed after synchronization')
 reg=read(repo/'source/films/registry.json');entry=next(f for f in reg['films'] if f['slug']==c['slug'])
 if mode=='final' and not entry['storage_ready']:raise RuntimeError('Final package requires storage evidence; record it, run site again, and sync')
 dest=root/'work/site'/f'{mode}.tar.gz';dest.parent.mkdir(parents=True,exist_ok=True);env=os.environ.copy()
 for k in ['SITES_MEDIA_SEED','SITES_CMB_SEED','SITES_DARK_SEED','SITES_FILMS_STAGE']:env.pop(k,None)
 if mode=='stage':env['SITES_FILMS_STAGE']=c['slug']
 inputs={'head':head,'mode':mode,'video_sha':entry['sha256'],'builder':digest(SKILL/'scripts/site_workflow.py')}
 # Build logs and transient state live in the project, not an untracked repository work directory.
 def run_build():
  log=root/'work'/f'site-{mode}.log'
  with log.open('w') as f:r=subprocess.run(['npm','run','build'],cwd=repo,env=env,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError(log.read_text()[-3000:])
  if git(repo,'status','--porcelain','--untracked-files=no'):raise RuntimeError('Build changed tracked files; synchronize them before packaging')
  with tarfile.open(dest,'w:gz') as tar:
   for path in ['.openai/hosting.json','dist/server/index.js']:tar.add(repo/path,arcname=path)
 stage(root,'package_'+mode,inputs,[dest],run_build)
 publish=read(root/'work/publish.json') if (root/'work/publish.json').exists() else {}
 old=publish.get(mode+'_package',{})
 record={'archive':str(dest),'archive_sha256':digest(dest),'commit_sha':head,'project_id':info['project_id']}
 if old and old!=record:
  keep_history(publish,[mode+'_saved',mode+'_deployed'],'packaged source changed')
 publish[mode+'_package']=record;write(root/'work/publish.json',publish);print(json.dumps(record))

def normalize(result):return result.get('structuredContent',result)
def receipt(root,phase,result):
 info=read(root/'work/site.json');state=read(root/'work/publish.json') if (root/'work/publish.json').exists() else {};data=normalize(result)
 if (data.get('id') if phase=='site_access' else data.get('project_id'))!=info['project_id']:raise ValueError('Receipt belongs to a different project')
 if phase=='site_access':
  policy=data.get('access_policy') or {};users=policy.get('allowed_users') or []
  private=data.get('current_user_role')=='owner' and data.get('access_mode')=='custom' and bool(users) and all(u.get('role')=='owner' and u.get('account_user_id') for u in users) and set(policy.get('allowed_account_user_ids') or [])=={u['account_user_id'] for u in users} and not policy.get('allowed_groups') and not policy.get('allowed_workspace_group_ids') and not policy.get('allowed_tenant_group_ids') and not policy.get('external_visitor_count') and not policy.get('allowed_editors')
  state[phase]={'owner_private':private,'access_mode':data.get('access_mode'),'observed_epoch':time.time()}
 elif phase=='storage_ready':
  expected='MEDIA_SEED_READY '+info['key']+' '+str(info['bytes']);messages=[]
  for event in data.get('events',[]):
   message=event.get('source',{}).get('message') or event.get('$metadata',{}).get('message','')
   if message==expected:messages.append(message)
  if not messages:raise ValueError('No exact storage-ready key/size evidence in the returned production logs')
  deployed=state.get('stage_deployed',{})
  if deployed.get('status')!='succeeded':raise ValueError('Stage publication has not succeeded')
  state[phase]={'project_id':info['project_id'],'key':info['key'],'bytes':info['bytes'],'observed_epoch':time.time()}
 elif phase.endswith('_saved'):
  mode=phase.split('_')[0];pack=state.get(mode+'_package',{})
  if data.get('source',{}).get('commit_sha')!=pack.get('commit_sha') or not data.get('id'):raise ValueError('Saved version does not match the packaged source')
  state[phase]={'id':data['id'],'project_id':data['project_id'],'commit_sha':pack['commit_sha']}
 else:
  mode=phase.split('_')[0];saved=state.get(mode+'_saved',{})
  if data.get('version_id')!=saved.get('id') or not data.get('id'):raise ValueError('Deployment does not own the recorded saved version')
  state[phase]={k:data.get(k) for k in ['id','project_id','version_id','status','url','failure_message']}
 write(root/'work/publish.json',state);print(json.dumps({'recorded':phase}))

def next_action(root):
 info=read(root/'work/site.json');state=read(root/'work/publish.json') if (root/'work/publish.json').exists() else {};project=info['project_id']
 c=read(root/'video.json')
 if site_signature(root,c)!=info.get('site_signature'):return {'local':'site metadata changed; run site, sync and package before publishing'}
 mode='final' if state.get('storage_ready') else 'stage';pack=state.get(mode+'_package');saved=state.get(mode+'_saved');deployed=state.get(mode+'_deployed')
 if not pack:return {'local':'site, sync source and package --mode '+mode}
 if not saved:return {'tool':'mcp__codex_apps__sites_save_site_version','args':{'project_id':project,'commit_sha':pack['commit_sha'],'archive':pack['archive']},'record_as':mode+'_saved'}
 if not state.get('site_access'):return {'tool':'mcp__codex_apps__sites_get_site','args':{'project_id':project},'record_as':'site_access'}
 if deployed and deployed.get('status')=='failed':return {'needs_repair':True,'deployment_id':deployed['id'],'version_id':saved['id'],'failure':deployed.get('failure_message'),'instruction':'Repair the observed failure before retrying; keep the existing version/deployment IDs.'}
 if not deployed:return {'tool':('mcp__codex_apps__sites_deploy_private_site_version' if state['site_access']['owner_private'] else 'mcp__codex_apps__sites_deploy_site_version'),'args':{'project_id':project,'version_id':saved['id']},'record_as':mode+'_deployed'}
 if deployed['status'] in ['pending','building','publishing']:return {'tool':'mcp__codex_apps__sites_get_deployment_status','args':{'project_id':project,'deployment_id':deployed['id']},'record_as':mode+'_deployed'}
 if deployed['status']!='succeeded':raise RuntimeError('Unrecognized deployment state')
 if mode=='stage':return {'tool':'mcp__codex_apps__sites_get_site_worker_logs','args':{'project_id':project,'errors_only':False,'since_minutes':5,'limit':100},'record_as':'storage_ready'}
 return {'done':True,'url':deployed['url'],'video_path':info['asset_route']}

def dispatch(args,root,c):
 if args.cmd in ['site','package']:
  with repo_lock(args.repo.resolve()):
   if args.cmd=='site':integrate(root,c,args.repo)
   else:package(root,c,args.repo,args.mode)
 elif args.cmd=='receipt':
  import sys
  receipt(root,args.phase,json.load(sys.stdin))
 else:print(json.dumps(next_action(root),ensure_ascii=False,indent=2))
