"""Disposable-lab OpenBao initialization/API client; never print credentials."""
import base64,contextlib,json,os,secrets,ssl,subprocess,time,urllib.error,urllib.request
from pathlib import Path
os.umask(0o077)
FOLDER=Path.home()/'.config/deployment-secret-validation'
FOLDER.mkdir(parents=True,exist_ok=True,mode=0o700);FOLDER.chmod(0o700)
def command(args,check=True):
 r=subprocess.run(args,capture_output=True,text=True,timeout=25)
 if check and r.returncode:raise RuntimeError('Command failed: '+args[0]+' '+args[1]+' (output withheld)')
 return r

def initialize():
 dest=FOLDER/'openbao-init.json'
 for attempt in range(360):
  try:r=command(['kubectl','-n','secrets','exec','openbao-0','--','bao','status','-format=json'],False);status=json.loads(r.stdout)
  except (ValueError,subprocess.TimeoutExpired):time.sleep(2);continue
  if not status['initialized']:
   with dest.open('x') as f:
    r=command(['kubectl','-n','secrets','exec','openbao-0','--','bao','operator','init','-key-shares=1','-key-threshold=1','-format=json'])
    json.dump(json.loads(r.stdout),f)
   dest.chmod(0o600)
  if not dest.exists():raise RuntimeError('Missing original initialization material')
  if status.get('sealed',True):
   key=json.loads(dest.read_text())['unseal_keys_b64'][0]
   command(['kubectl','-n','secrets','exec','openbao-0','--','bao','operator','unseal',key])
  else:print('Single lab Raft replica initialized and unsealed; recovery material mode0600',flush=True);return
  time.sleep(1)
 raise RuntimeError('OpenBao startup timed out')

class ApiError(Exception):
 def __init__(self,status):self.status=status;super().__init__('OpenBao API status '+str(status))

class Backend:
 def __enter__(self):
  material=FOLDER/'openbao-init.json'
  assert not material.stat().st_mode & 0o077
  self.root=json.loads(material.read_text())['root_token']
  ca=command(['kubectl','-n','secrets','get','secret','openbao-server-tls','-o','jsonpath={.data.ca\\.crt}']).stdout
  cafile=FOLDER/'ca.crt';cafile.write_bytes(base64.b64decode(ca))
  self.client=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(cafile))))
  self.log=(FOLDER/'forward.log').open('w')
  self.forward=subprocess.Popen(['kubectl','-n','secrets','port-forward','pod/openbao-0','18200:8200'],stdin=subprocess.DEVNULL,stdout=self.log,stderr=self.log)
  for _ in range(40):
   try:self.call('sys/health');return self
   except Exception:time.sleep(.5)
  raise RuntimeError('Verified OpenBao port forward unavailable')
 def __exit__(self,*args):self.forward.terminate();self.forward.wait(timeout=10);self.log.close()
 def call(self,path,data=None,token=None,method=None):
  request=urllib.request.Request('https://127.0.0.1:18200/v1/'+path,data=None if data is None else json.dumps(data).encode(),headers={'X-Vault-Token':self.root if token is None else token,'Content-Type':'application/json'},method=method)
  try:
   with self.client.open(request,timeout=15) as response:
    body=response.read();return json.loads(body) if body else None
  except urllib.error.HTTPError as error:raise ApiError(error.code) from None
 def state(self):return json.loads((FOLDER/'application-values.json').read_text())
 def save(self,state):(FOLDER/'application-values.json').write_text(json.dumps(state))
 def configure(self,mode,repo):
  if 'kv/' not in self.call('sys/mounts')['data']:self.call('sys/mounts/kv',{'type':'kv','options':{'version':'2'}})
  if 'kubernetes/' not in self.call('sys/auth')['data']:self.call('sys/auth/kubernetes',{'type':'kubernetes'})
  self.call('auth/kubernetes/config',{'kubernetes_host':'https://kubernetes.default.svc:443'})
  component='external-secrets' if mode=='eso' else 'openbao-injector';purpose='environment' if mode=='eso' else 'files'
  policy=(Path(repo)/'flux/infrastructure/primitives/deployment/opt-in'/component/'policy.hcl').read_text()
  state={}
  for app in ['api','worker']:
   identity=app+'-application-'+component
   self.call('sys/policies/acl/'+identity,{'policy':policy.replace('applications/application/','applications/'+app+'/')})
   role={'bound_service_account_names':[identity],'bound_service_account_namespaces':['demo'],'audience':'openbao','token_policies':[identity],'token_no_default_policy':True,'token_ttl':'15m','token_max_ttl':'1h'}
   if mode=='injector':role.update(token_ttl='30s',token_max_ttl='2m')
   self.call('auth/kubernetes/role/'+identity,role)
   state[app]={'APP_PASSWORD':secrets.token_urlsafe(32)}
   self.call('kv/data/applications/'+app+'/'+purpose,{'data':state[app]})
  self.save(state)
  print('Two isolated application policies, roles and randomized KV values provisioned; values withheld',flush=True)

if __name__=='__main__':
 import sys
 initialize()
 with Backend() as backend:backend.configure(sys.argv[1],sys.argv[2])
 print('BACKEND_READY',flush=True)
