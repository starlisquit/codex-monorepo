import contextlib,json,os,socket,subprocess,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone
from backend import FOLDER,command
os.umask(0o077)
def k(*args):return command(['kubectl',*args]).stdout
def get(kind,name,ns):return json.loads(k('-n',ns,'get',kind,name,'-o','json'))
def ready(obj):return any(c['type']=='Ready' and c['status']=='True' for c in obj.get('status',{}).get('conditions',[]))
def wait(label,fn,timeout=900):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:
   v=fn()
   if v:return v
  except Exception:pass
  time.sleep(2)
 raise RuntimeError('Timed out: '+label)
def wait_contracts():wait('all application credential contracts',lambda:json.loads((Path.home()/'contracts-evidence.json').read_text())['result']=='passed')
def wait_release(name,ns):return wait('release '+name,lambda:ready(get('helmrelease',name,ns)))
def pods(ns,label):return json.loads(k('-n',ns,'get','pods','-l',label,'-o','json'))['items']
def pod(ns,label):return next(p for p in pods(ns,label) if not p['metadata'].get('deletionTimestamp'))
class Forward:
 def __init__(self,ns,target,remote,local):self.ns=ns;self.target=target;self.remote=remote;self.local=local
 def __enter__(self):
  self.log=(FOLDER/('forward-'+str(self.local)+'.log')).open('w');self.process=subprocess.Popen(['kubectl','-n',self.ns,'port-forward',self.target,f'{self.local}:{self.remote}'],stdin=subprocess.DEVNULL,stdout=self.log,stderr=self.log)
  def available():
   with socket.create_connection(('127.0.0.1',self.local),timeout=1):return True
  wait('port forward '+self.target,available,30);return self
 def __exit__(self,*args):self.process.terminate();self.process.wait(timeout=10);self.log.close()
 def request(self,path='/',data=None,headers=None,method=None,statuses=(200,201,202,204)):
  if isinstance(data,(dict,list)):data=json.dumps(data).encode();headers={'Content-Type':'application/json',**(headers or {})}
  req=urllib.request.Request(f'http://127.0.0.1:{self.local}'+path,data=data,headers=headers or {},method=method)
  client=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  try:
   with client.open(req,timeout=20) as r:status=r.status;raw=r.read()
  except urllib.error.HTTPError as e:status=e.code;raw=e.read()
  if status not in statuses:raise RuntimeError('Application HTTP status '+str(status)+' for '+path.split('?')[0])
  try:return status,json.loads(raw)
  except (ValueError,UnicodeDecodeError):return status,raw.decode(errors='replace')
def values():return json.loads((FOLDER/'application-values.json').read_text())
class Evidence:
 def __init__(self,mode):self.data={'mode':mode,'started_at':datetime.now(timezone.utc).isoformat(),'checks':{}}
 def record(self,name,value=True):self.data['checks'][name]=value;self.save();print(name+': passed',flush=True)
 def save(self):(Path.home()/'application-evidence.json').write_text(json.dumps(self.data,indent=2)+'\n')
 def finish(self):self.data.update(result='passed',completed_at=datetime.now(timezone.utc).isoformat());self.save();print('APPLICATIONS_PASSED',flush=True)
