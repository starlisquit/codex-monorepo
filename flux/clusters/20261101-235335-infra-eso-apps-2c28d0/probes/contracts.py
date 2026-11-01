import base64,hashlib,json,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
import yaml
from backend import Backend,ApiError,FOLDER,command
RUN=Path(sys.argv[1]);inventory=json.loads((RUN/'inventory.json').read_text())
def k(*args):return command(['kubectl',*args]).stdout
def get(kind,name,ns):return json.loads(k('-n',ns,'get',kind,name,'-o','json'))
def wait(label,fn,timeout=900):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:
   v=fn()
   if v:return v
  except Exception:pass
  time.sleep(2)
 raise RuntimeError('Timed out: '+label)
def ready(obj):return any(c['type']=='Ready' and c['status']=='True' for c in obj.get('status',{}).get('conditions',[]))
def denied(fn):
 try:fn()
 except ApiError as e:assert e.status in [400,403];return e.status
 raise AssertionError('Expected denial')
def main():
 wait('backend',lambda:'BACKEND_READY' in (Path.home()/'backend.log').read_text())
 values=json.loads((FOLDER/'application-values.json').read_text());e={'mode':inventory['mode'],'contracts':[],'auth':[]}
 for item in inventory['credentials']:
  ns=item['namespace'];name=item['target'];wait('Secret sync '+name,lambda:ready(get('externalsecret',name,ns)))
  secret=get('secret',name,ns);data={key:base64.b64decode(value).decode() for key,value in secret['data'].items()}
  expected=values[name].copy()
  if name=='gitlab-runner-auth':expected['runner-registration-token']=''
  assert data==expected,'Delivered Secret value mismatch'
  assert any(o['kind']=='ExternalSecret' and o['name']==name for o in secret['metadata']['ownerReferences'])
  e['contracts'].append({'namespace':ns,'name':name,'keys':sorted(data),'sha256':{key:hashlib.sha256(value.encode()).hexdigest() for key,value in data.items()},'ready':True,'correct_owner':True})
  print(name+': synced and exact values verified',flush=True)
 with Backend() as backend:
  for relative in inventory['opt_ins']:
   p=Path.home()/'repo/flux/infrastructure'/relative;store=yaml.safe_load((p/'secretstore.yaml').read_text());ns=store['metadata']['namespace'];auth=store['spec']['provider']['vault']['auth']['kubernetes'];sa=auth['serviceAccountRef']['name'];role=auth['role']
   jwt=k('-n',ns,'create','token',sa,'--audience=openbao','--duration=10m').strip()
   token=backend.call('auth/kubernetes/login',{'role':role,'jwt':jwt},token='')['auth']['client_token']
   own=yaml.safe_load_all((p/'externalsecrets.yaml').read_text());ownpath=next(own)['spec']['data'][0]['remoteRef']['key']
   backend.call('kv/data/'+ownpath,token=token)
   cross=denied(lambda:backend.call('kv/data/forbidden/other-application',token=token))
   badjwt=k('-n',ns,'create','token',sa,'--audience=wrong-audience','--duration=10m').strip()
   badaud=denied(lambda:backend.call('auth/kubernetes/login',{'role':role,'jwt':badjwt},token=''))
   e['auth'].append({'store':store['metadata']['name'],'namespace':ns,'own_path_read':True,'cross_path_http':cross,'wrong_audience_http':badaud})
 e['completed_at']=datetime.now(timezone.utc).isoformat();e['result']='passed';(Path.home()/'contracts-evidence.json').write_text(json.dumps(e,indent=2)+'\n');print('CONTRACTS_PASSED',flush=True)
if __name__=='__main__':main()
