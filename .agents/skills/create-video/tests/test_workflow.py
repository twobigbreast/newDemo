"""Behavior tests with a real completed 60s MP4 and an isolated local Git/Worker fixture.
No new film, network request, production deployment, model download or TTS inference.
"""
import base64,contextlib,importlib.util,io,json,os,shutil,subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
SKILL=Path(__file__).resolve().parents[1];sys.path.insert(0,str(SKILL/'scripts'))
import video
from site_workflow import integrate,package,receipt,next_action
from sync_source import sync
SAMPLE=Path(os.environ.get('CREATE_VIDEO_SAMPLE','/workspace/work/dark-matter'))
REPO=Path(os.environ.get('CREATE_VIDEO_REPO','/workspace/work/site'))

def run(args,cwd=None,env=None):return subprocess.run(args,cwd=cwd,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True).stdout
class Workflow(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not (SAMPLE/'output/dark-matter-60s.mp4').exists():raise unittest.SkipTest('Set CREATE_VIDEO_SAMPLE to the completed film fixture')
  cls.tmp=tempfile.TemporaryDirectory(prefix='create-video-',dir='/workspace/work');cls.base=Path(cls.tmp.name);cls.project=cls.base/'film';run([sys.executable,str(SKILL/'scripts/video.py'),'init','--project',str(cls.project),'--template','dark-matter','--slug','fixture'])
  for name in ['soundtrack.m4a','voice-timing.json']:shutil.copyfile(SAMPLE/'assets'/name,cls.project/'assets'/name)
  shutil.copyfile(SAMPLE/'output/dark-matter-60s.mp4',cls.project/'output/fixture-60s.mp4');shutil.copyfile(SAMPLE/'output/render-results.json',cls.project/'output/render-results.json')
  cls.config=video.load(cls.project)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_01_real_video_and_cached_keyframes(self):
  video.keyframes(self.project,self.config);contact=self.project/'work/keyframes.jpg';stamp=contact.stat().st_mtime_ns
  self.assertFalse(video.keyframes(self.project,self.config));self.assertEqual(stamp,contact.stat().st_mtime_ns)
  video.review(self.project,self.config,'Fixture: checked six mechanisms, labels and final-font frame layout')
  self.assertTrue(video.verify(self.project,self.config));self.assertFalse(video.verify(self.project,self.config))
  validation=video.read(self.project/'output/validation.json');self.assertTrue(validation['passed']);self.assertEqual(1800,validation['decoded_frames'])
  video.docs(self.project,self.config);self.assertTrue((self.project/'SCIENCE_NOTES.md').exists())
 def test_02_page_edits_do_not_invalidate_render_inputs(self):
  before=video.signature(video.visual(self.project,self.config));changed=json.loads(json.dumps(self.config));changed['page']['description']='Only the webpage changed';changed['science']['limitations'].append('Credit correction')
  self.assertEqual(before,video.signature(video.visual(self.project,changed)))
  changed['scenes'][0]['title']='A different on-screen title';self.assertNotEqual(before,video.signature(video.visual(self.project,changed)))
  sentinel=self.project/'work/sentinel';calls=[]
  def action():calls.append(1);sentinel.write_text('completed')
  video.stage(self.project,'test-cache',{'visual':'A'},[sentinel],action);video.stage(self.project,'test-cache',{'visual':'A'},[sentinel],action);self.assertEqual(1,len(calls))
  sentinel.write_text('unexpected modification');video.stage(self.project,'test-cache',{'visual':'A'},[sentinel],action);self.assertEqual(2,len(calls))
 def test_03_stale_review_is_rejected(self):
  changed=json.loads(json.dumps(self.config));changed['scenes'][0]['title']='Changed after inspection'
  with self.assertRaisesRegex(ValueError,'stale'):video.review(self.project,changed,'This must not accept old images')
  with self.assertRaisesRegex(RuntimeError,'review'):video.render(self.project,changed)
 def test_04_generated_site_two_publications_and_resume(self):
  repo=self.base/'site';repo.mkdir();self.repo=repo
  for folder in ['.openai','worker','scripts','dist']:(repo/folder).mkdir()
  video.write(repo/'.openai/hosting.json',{'project_id':'fixture-project','r2':'BUCKET'})
  (repo/'.gitignore').write_text('dist/server/\n')
  (repo/'package.json').write_text(json.dumps({'scripts':{'build':'node scripts/build-worker.mjs'}}))
  (repo/'dist/science.html').write_text('<html><div class="light-links"></div></html>');(repo/'dist/index.html').write_text('<html>fixture</html>')
  shutil.copyfile(REPO/'worker/index.template.js',repo/'worker/index.template.js')
  (repo/'scripts/build-worker.mjs').write_text('''import{readFile,readdir,mkdir,writeFile}from'node:fs/promises';import path from'node:path';import{createHash}from'node:crypto';import{fileURLToPath}from'node:url';
const root=path.resolve(fileURLToPath(new URL('..',import.meta.url)));const dist=path.join(root,'dist');
const assets = {};
const publicMedia={};const mediaSeeds = {};
async function walk(dir){for(const entry of await readdir(dir,{withFileTypes:true})){if(entry.name==='server')continue;const full=path.join(dir,entry.name);if(entry.isDirectory()){await walk(full);continue;}const rel='/'+path.relative(dist,full).split(path.sep).join('/');
      const bytes = await readFile(full);
assets[rel]={body:/\\.(html|md|srt)$/.test(rel)?bytes.toString():bytes.toString('base64'),encoding:/\\.(html|md|srt)$/.test(rel)?undefined:'base64',contentType:rel.endsWith('.html')?'text/html':rel.endsWith('.jpg')?'image/jpeg':'application/octet-stream'};
}}await walk(dist);let code=await readFile(path.join(root,'worker/index.template.js'),'utf8');code=code.replace('__STATIC_ASSETS__',()=>JSON.stringify(assets)).replace('__PUBLIC_MEDIA__',()=>JSON.stringify(publicMedia)).replace('__MEDIA_SEEDS__',()=>JSON.stringify(mediaSeeds));await mkdir(path.join(dist,'server'),{recursive:true});await writeFile(path.join(dist,'server/index.js'),code);
''')
  run(['git','init','-b','main'],repo);run(['git','add','.'],repo);run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture'],repo)
  remote=self.base/'remote.git';run(['git','init','--bare',str(remote)]);run(['git','push',str(remote),'main'],repo)
  credential={'auth_mode':'work_proxy','remote_url':str(remote),'branch':'main'}
  integrate(self.project,self.config,repo);registry=video.read(repo/'source/films/registry.json');entry=registry['films'][0];self.assertFalse(entry['storage_ready'])
  page=(repo/'dist/science/fixture.html').read_text();self.assertIn('preload="none"',page);self.assertNotIn('autoplay',page);self.assertNotIn('source.zip',page)
  self.assertFalse((repo/'dist/science/fixture-media/source').exists())
  normal=subprocess.run(['npm','run','build'],cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);self.assertNotEqual(0,normal.returncode);self.assertIn('unverified',normal.stdout)
  sync(self.project,repo,credential,'stage fixture');package(self.project,self.config,repo,'stage');state=video.read(self.project/'work/publish.json');pack=state['stage_package']
  with tarfile.open(pack['archive']) as tar:self.assertEqual({'.openai/hosting.json','dist/server/index.js'},set(tar.getnames()))
  initial=next_action(self.project);self.assertIn('save_site_version',initial['tool']);self.assertEqual(initial,next_action(self.project))
  receipt(self.project,'stage_saved',{'project_id':'fixture-project','id':'fixture-version-stage','source':{'commit_sha':pack['commit_sha']}})
  self.assertIn('get_site',next_action(self.project)['tool']);receipt(self.project,'site_access',{'id':'fixture-project','access_mode':'public','current_user_role':'owner'})
  action=next_action(self.project);self.assertEqual('fixture-version-stage',action['args']['version_id'])
  pending={'project_id':'fixture-project','id':'fixture-deployment-stage','version_id':'fixture-version-stage','status':'publishing'};receipt(self.project,'stage_deployed',pending);self.assertIn('get_deployment_status',next_action(self.project)['tool'])
  pending.update(status='succeeded',url='https://fixture.invalid');receipt(self.project,'stage_deployed',pending)
  with self.assertRaisesRegex(ValueError,'exact storage'):receipt(self.project,'storage_ready',{'project_id':'fixture-project','events':[]})
  receipt(self.project,'storage_ready',{'project_id':'fixture-project','events':[{'source':{'message':f"MEDIA_SEED_READY {entry['key']} {entry['bytes']}"}}]})
  integrate(self.project,self.config,repo);self.assertTrue(video.read(repo/'source/films/registry.json')['films'][0]['storage_ready'])
  sync(self.project,repo,credential,'final fixture');package(self.project,self.config,repo,'final')
  code=(repo/'dist/server/index.js').read_text();sample=base64.b64encode((self.project/'output/fixture-60s.mp4').read_bytes()[:60]).decode();self.assertNotIn(sample,code)
  pack=video.read(self.project/'work/publish.json')['final_package'];receipt(self.project,'final_saved',{'project_id':'fixture-project','id':'fixture-version-final','source':{'commit_sha':pack['commit_sha']}})
  receipt(self.project,'final_deployed',{'project_id':'fixture-project','id':'fixture-deployment-final','version_id':'fixture-version-final','status':'succeeded','url':'https://fixture.invalid'})
  self.assertTrue(next_action(self.project)['done']);self.assertNotIn('save_site_version',str(next_action(self.project)))
  # Validate the generated R2 route itself, not only its metadata.
  run(['node',str(SKILL/'tests/check-generated-worker.mjs'),str(repo),str(self.project/'output/fixture-60s.mp4')])
 def test_05_private_audience_and_failure_preserve_ids(self):
  receipt(self.project,'site_access',{'id':'fixture-project','access_mode':'custom','current_user_role':'owner','access_policy':{'allowed_users':[{'role':'owner','account_user_id':'fixture-owner'}],'allowed_account_user_ids':['fixture-owner'],'allowed_groups':[]}})
  state=video.read(self.project/'work/publish.json');state.pop('final_deployed');video.write(self.project/'work/publish.json',state);self.assertIn('deploy_private',next_action(self.project)['tool'])
  receipt(self.project,'final_deployed',{'project_id':'fixture-project','id':'fixture-failed-deployment','version_id':'fixture-version-final','status':'failed','failure_message':'Observed fixture failure'})
  self.assertTrue(next_action(self.project)['needs_repair']);self.assertEqual('fixture-version-final',next_action(self.project)['version_id'])
 def test_06_page_revision_reuses_storage_but_not_old_success(self):
  original=video.read(self.project/'video.json');changed=json.loads(json.dumps(original));changed['page']['description']='A new webpage description'
  video.write(self.project/'video.json',changed)
  try:
   integrate(self.project,changed,self.base/'site');state=video.read(self.project/'work/publish.json')
   self.assertIn('storage_ready',state);self.assertNotIn('final_saved',state);self.assertNotIn('final_deployed',state);self.assertTrue(state['history']);self.assertIn('final',next_action(self.project)['local'])
  finally:video.write(self.project/'video.json',original)
 def test_07_cmb_template_keyframes(self):
  project=self.base/'cmb';run([sys.executable,str(SKILL/'scripts/video.py'),'init','--project',str(project),'--title','CMB 科普','--slug','cmb-fixture'])
  self.assertEqual('cmb',video.read(project/'video.json')['template'])
  sample=SAMPLE.parent/'cmb'
  for name in ['soundtrack.m4a','voice-timing.json']:shutil.copyfile(sample/'assets'/name,project/'assets'/name)
  self.assertTrue(video.keyframes(project,video.load(project)));self.assertTrue((project/'output/poster.jpg').is_file())
if __name__=='__main__':unittest.main(verbosity=2)
