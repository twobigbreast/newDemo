"""Synchronize only generator-owned files; credentials are received through stdin and never saved."""
import base64,json,os,subprocess,time
from pathlib import Path
from video import read,write
from site_workflow import git,repo_lock

def sync(root,repo,credential,message):
 repo=repo.resolve();info=read(root/'work/site.json')
 if Path(info['repo']).resolve()!=repo:raise ValueError('Wrong source checkout')
 env=os.environ.copy()
 if credential.get('auth_mode')!='work_proxy':
  if not credential.get('token'):raise ValueError('Repository credential lacks a token')
  n=int(env.get('GIT_CONFIG_COUNT','0'));env['GIT_CONFIG_COUNT']=str(n+1);env[f'GIT_CONFIG_KEY_{n}']='http.extraHeader';env[f'GIT_CONFIG_VALUE_{n}']='Authorization: Basic '+base64.b64encode(('x-access-token:'+credential['token']).encode()).decode()
 def run(*args):return subprocess.run(['git',*args],cwd=repo,env=env,check=True)
 owned=read(root/'work/site-files.json');allowed=set(owned)
 for rel in owned:
  if not (repo/rel).resolve().is_relative_to(repo):raise ValueError('Owned file escapes the checkout')
 staged=git(repo,'diff','--cached','--name-only').splitlines()
 if any(p not in allowed for p in staged):raise RuntimeError('Unrelated user changes are already staged; keep them out of the generated commit')
 with repo_lock(repo):
  run('add','--',*owned)
  if subprocess.run(['git','diff','--cached','--quiet'],cwd=repo).returncode:
   run('-c','user.name=Codex','-c','user.email=codex@openai.com','commit','-m',message)
  # Do not rebase through unrelated unstaged edits or force-push.
  if git(repo,'status','--porcelain','--untracked-files=no'):raise RuntimeError('Unrelated tracked changes remain; resolve them before synchronization')
  run('fetch',credential['remote_url'],credential['branch']);run('rebase','FETCH_HEAD')
  run('push',credential['remote_url'],'HEAD:'+credential['branch']);head=git(repo,'rev-parse','HEAD')
  write(root/'work/sync.json',{'head':head,'project_id':info['project_id'],'pushed_epoch':time.time()});print(json.dumps({'head':head,'pushed':True}))
