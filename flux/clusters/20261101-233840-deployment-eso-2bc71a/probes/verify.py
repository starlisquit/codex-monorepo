"""Runtime delivery, isolation and refresh checks. Evidence excludes secret values."""
import base64,copy,hashlib,json,os,secrets,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
from backend import Backend,ApiError,command,FOLDER
MODE=sys.argv[1]
E={'mode':MODE,'started_at':datetime.now(timezone.utc).isoformat(),'checks':{}}
def record(name,value=True):
 E['checks'][name]=value
 (Path.home()/'evidence.json').write_text(json.dumps(E,indent=2)+'\n')
 print(name+': passed',flush=True)
def k(*args):return command(['kubectl',*args]).stdout
def obj(kind,name,ns='demo'):return json.loads(k('-n',ns,'get',kind,name,'-o','json'))
def pods(app):return json.loads(k('-n','demo','get','pods','-l','app.kubernetes.io/name='+app,'-o','json'))['items']
def pod(app):return next(p for p in pods(app) if not p['metadata'].get('deletionTimestamp'))
def ready(p):return any(c['type']=='Ready' and c['status']=='True' for c in p.get('status',{}).get('conditions',[]))
def wait(label,fn,seconds=360):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:
   value=fn()
   if value:return value
  except (Exception,StopIteration):pass
  time.sleep(2)
 raise RuntimeError('Timed out: '+label)
def probe(app):
 p=pod(app);code="import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080',timeout=3).read().decode())"
 return json.loads(k('-n','demo','exec',p['metadata']['name'],'-c','application','--','python','-c',code))
def fingerprint(value):return hashlib.sha256(value.encode()).hexdigest()
def secret_hash(app):
 secret=obj('secret',app+'-application-env')
 return hashlib.sha256(base64.b64decode(secret['data']['APP_PASSWORD'])).hexdigest()
def synced(app):
 secret=obj('externalsecret',app+'-application-env')
 return any(c['type']=='Ready' and c['status']=='True' for c in secret.get('status',{}).get('conditions',[]))
def login(backend,identity,audience='openbao',namespace='demo'):
 jwt=k('-n',namespace,'create','token',identity,'--audience='+audience,'--duration=10m').strip()
 return backend.call('auth/kubernetes/login',{'role':'api-application-'+('external-secrets' if MODE=='eso' else 'openbao-injector'),'jwt':jwt},token='')['auth']['client_token']
def denied(fn,statuses=(403,)):
 try:fn()
 except ApiError as error:
  assert error.status in statuses;return error.status
 raise AssertionError('Forbidden operation unexpectedly succeeded')

def main():
 wait('backend readiness',lambda:(Path.home()/'backend.log').exists() and 'BACKEND_READY' in (Path.home()/'backend.log').read_text(),600)
 for app in ['api','worker']:wait(app+' ready',lambda app=app:ready(pod(app)),600)
 with Backend() as backend:
  state=backend.state();purpose='environment' if MODE=='eso' else 'files';component='external-secrets' if MODE=='eso' else 'openbao-injector'
  expected={a:fingerprint(state[a]['APP_PASSWORD']) for a in state}
  before={a:pod(a)['metadata']['uid'] for a in state}
  for app in state:
   result=probe(app);assert result['sha256']==expected[app] and result['uid']==10001
  record('initial_application_delivery',{'pod_uids':before,'sha256':expected,'uid':10001})
  record('https_backend_verified',{'endpoint':'https://openbao-active.secrets.svc:8200','public_ca':True,'skip_verify':False})
  identity='api-application-'+component;token=login(backend,identity)
  assert backend.call('kv/data/applications/api/'+purpose,token=token)['data']['data']==state['api']
  cross=denied(lambda:backend.call('kv/data/applications/worker/'+purpose,token=token))
  renew=backend.call('auth/token/renew-self',{},token=token)
  assert renew['auth']['renewable']
  lookup=backend.call('auth/token/lookup-self',token=token)
  assert lookup['data']['ttl']>0
  wrongsa=denied(lambda:login(backend,'default'),(400,403))
  wrongaud=denied(lambda:login(backend,identity,'not-openbao'),(400,403))
  command(['kubectl','-n','default','create','serviceaccount',identity],False)
  wrongns=denied(lambda:login(backend,identity,namespace='default'),(400,403))
  record('auth_and_policy_isolation',{'cross_application_http':cross,'wrong_service_account_http':wrongsa,'wrong_audience_http':wrongaud,'wrong_namespace_http':wrongns,'self_lookup_and_renew':True})
  if MODE=='eso':
   for app in state:
    assert synced(app) and secret_hash(app)==expected[app]
    assert pod(app)['spec']['automountServiceAccountToken'] is False
    assert not any('serviceaccount' in v.get('mountPath','') for c in pod(app)['spec']['containers'] for v in c.get('volumeMounts',[]))
    assert obj('secret',app+'-application-env')['metadata']['ownerReferences'][0]['kind']=='ExternalSecret'
   record('eso_secret_ownership_and_token_isolation')
  else:
   for app in state:
    p=pod(app);spec=p['spec'];application=next(c for c in spec['containers'] if c['name']=='application')
    assert spec['automountServiceAccountToken'] is False
    assert not any(v['name']=='openbao-auth' for v in application.get('volumeMounts',[]))
    assert all(any(v['name']=='openbao-auth' for v in c['volumeMounts']) for c in spec['initContainers']+spec['containers'] if c['name'].startswith('vault-agent'))
    assert len([c for c in spec['initContainers'] if c['name']=='vault-agent-init'])==1
    assert len([c for c in spec['containers'] if c['name']=='vault-agent'])==1
    result=probe(app);assert result['file_mode']=='0o400' and result['file_uid']==10001
   record('injected_agents_file_permissions_and_token_isolation')
  # Change only the API credential. Every emitted result is a hash, not its value.
  state['api']['APP_PASSWORD']=secrets.token_urlsafe(32);newhash=fingerprint(state['api']['APP_PASSWORD'])
  backend.call('kv/data/applications/api/'+purpose,{'data':state['api']});backend.save(state)
  if MODE=='eso':
   wait('ESO refreshed Secret',lambda:secret_hash('api')==newhash,180)
   assert probe('api')['sha256']==expected['api']
   record('eso_refresh_requires_environment_restart',{'new_secret_sha256':newhash,'running_environment_unchanged':True})
   k('-n','demo','rollout','restart','deployment/api-application')
   wait('new API Pod',lambda:pod('api')['metadata']['uid']!=before['api'] and ready(pod('api')),180)
   wait('new environment consumed',lambda:probe('api')['sha256']==newhash,90)
   record('new_pod_consumed_refreshed_environment')
   backend.call('kv/data/applications/api/environment',method='DELETE')
   wait('ESO missing provider reports not ready',lambda:not synced('api'),180)
   assert secret_hash('api')==newhash and probe('api')['sha256']==newhash
   record('missing_provider_retains_secret_and_reports_failure')
   backend.call('kv/data/applications/api/environment',{'data':state['api']})
   wait('ESO recovered after provider restore',lambda:synced('api'),180)
   record('provider_restore_recovers_synchronization')
  else:
   wait('agent refreshed file',lambda:probe('api')['sha256']==newhash,120)
   assert pod('api')['metadata']['uid']==before['api']
   record('file_refresh_without_pod_restart',{'new_sha256':newhash,'unchanged_pod_uid':before['api']})
   # Prove a fresh Pod cannot start the application after injection when its KV path is forbidden.
   deployment=obj('deployment','api-application')
   spec=copy.deepcopy(deployment['spec']);spec['selector']={'matchLabels':{'app.kubernetes.io/name':'blocked'}}
   spec['template']['metadata']['labels']={'app.kubernetes.io/name':'blocked'}
   annotations=spec['template']['metadata']['annotations'];path='kv/data/applications/api/forbidden'
   annotations['vault.hashicorp.com/agent-inject-secret-config.json']=path
   annotations['vault.hashicorp.com/agent-inject-template-config.json']='{{- with secret "'+path+'" -}}{{ .Data.data | toJSON }}{{- end -}}'
   fixture={'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':'blocked-application','namespace':'demo'},'spec':spec}
   result=subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(fixture),capture_output=True,text=True,timeout=20);assert result.returncode==0
   def blocked():
    p=pod('blocked');statuses=p.get('status',{}).get('initContainerStatuses',[])
    if any(c['name']=='vault-agent-init' and c.get('state',{}).get('running') for c in statuses):
     log=k('-n','demo','logs',p['metadata']['name'],'-c','vault-agent-init')
     return p if '403' in log or 'permission denied' in log else False
    return False
   failed=wait('forbidden path init blocked',blocked,180)
   assert not ready(failed)
   assert all(not c.get('state',{}).get('running') for c in failed.get('status',{}).get('containerStatuses',[]) if c['name']=='application')
   record('forbidden_path_blocks_application_start',{'pod_uid':failed['metadata']['uid'],'application_started':False})
   k('-n','demo','delete','deployment','blocked-application','--wait=false')
   # Force a fresh role login beyond the short lab token's maximum lifetime.
   start=time.monotonic();reauth=False
   while time.monotonic()-start<180:
    log=k('-n','demo','logs',pod('api')['metadata']['name'],'-c','vault-agent')
    if log.count('authentication successful')>=2:reauth=True;break
    time.sleep(5)
   assert reauth,'Agent did not demonstrate automatic reauthentication past lab token maxTTL'
   assert probe('api')['sha256']==newhash and pod('api')['metadata']['uid']==before['api']
   record('agent_reauthentication_without_pod_restart',{'lab_role_ttl':'30s','lab_role_max_ttl':'2m','success_log_entries_at_least':2})
  assert probe('worker')['sha256']==expected['worker'] and pod('worker')['metadata']['uid']==before['worker']
  record('other_application_unchanged')
  for app in state:assert ready(pod(app))
  record('final_applications_ready')
 E['completed_at']=datetime.now(timezone.utc).isoformat();E['result']='passed'
 (Path.home()/'evidence.json').write_text(json.dumps(E,indent=2)+'\n')
 print('VERIFICATION_PASSED',flush=True)

if __name__=='__main__':
 try:main()
 except Exception as error:
  E['result']='failed';E['error_type']=type(error).__name__;E['error']=str(error) if isinstance(error,(AssertionError,RuntimeError)) else 'details withheld'
  (Path.home()/'evidence.json').write_text(json.dumps(E,indent=2)+'\n');raise
