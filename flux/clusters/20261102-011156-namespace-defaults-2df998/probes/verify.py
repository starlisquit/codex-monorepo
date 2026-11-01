import base64,hashlib,json,sys,socket,ssl,struct,subprocess,time
from pathlib import Path
from runtime import *
from backend import Backend,NS,ApiError,FOLDER
MODE=sys.argv[1];RUN=sys.argv[2];e=Evidence('namespace-'+MODE)
ai=NS['NS_AI'];bao=NS['NS_SECRETS'];certns=NS['NS_CERTIFICATES'];dbns=NS['NS_DATABASES'];demo=NS['NS_DEMO']
wait('backend provisioning',lambda:'BACKEND_READY' in (Path.home()/'backend.log').read_text(),1200)
wait_release('litellm',ai)
wait('agent app',lambda:ready(pod(demo,'app.kubernetes.io/name=application')),900)
state=values()
# Every scoped role was provisioned from the post-build ConfigMap, not raw JSON.
cm=get('configmap','litellm-openbao-bootstrap',ai);role=json.loads(cm['data']['role.json']);assert role['bound_service_account_namespaces']==[ai]
with Backend() as backend:
 actual=backend.call('auth/kubernetes/role/'+role['token_policies'][0])['data'];assert actual['bound_service_account_namespaces']==[ai]
 jwt=k('-n',ai,'create','token','litellm-external-secrets','--audience=openbao','--duration=10m').strip()
 token=backend.call('auth/kubernetes/login',{'role':role['token_policies'][0],'jwt':jwt},token='')['auth']['client_token']
 backend.call('kv/data/infrastructure/ai/litellm/auth',token=token)
 try:backend.call('kv/data/forbidden/other-application',token=token)
 except ApiError as error:assert error.status==403
 else:raise AssertionError('Cross-path access accepted')
e.record('rendered_openbao_role_and_scoped_auth',{'namespace':ai,'role_namespace_matches':True,'cross_path_http':403})
for name,expected in [('litellm-auth',state['auth']),('litellm-provider-credentials',state['provider'])]:
 secret=get('secret',name,ai);actual={key:base64.b64decode(value).decode() for key,value in secret['data'].items()};assert actual==expected
 e.record(name+'_exact_delivery',{'namespace':ai,'sha256':{key:hashlib.sha256(value.encode()).hexdigest() for key,value in actual.items()}})
# TLS handshake uses the service's new namespace in the verified DNS name.
ca=get('configmap','platform-ca',ai)['data']['ca.crt'];cafile=FOLDER/'database-public-ca.crt';cafile.write_text(ca);context=ssl.create_default_context(cafile=str(cafile));host='litellm-db-rw.'+ai+'.svc.cluster.local'
def handshake(ctx,name):
 raw=socket.create_connection(('127.0.0.1',15432),timeout=8);raw.sendall(struct.pack('!II',8,80877103));assert raw.recv(1)==b'S'
 return ctx.wrap_socket(raw,server_hostname=name)
with Forward(ai,'service/litellm-db-rw',5432,15432):
 with handshake(context,host) as conn:details={'version':conn.version(),'serial':conn.getpeercert()['serialNumber'],'hostname':host}
 for ctx,name in [(context,'wrong-host.invalid'),(ssl.create_default_context(),host)]:
  try:
   with handshake(ctx,name):pass
  except ssl.SSLCertVerificationError:pass
  else:raise AssertionError('Invalid TLS trust/hostname accepted')
e.record('namespace_qualified_database_tls',details)
servercert=get('certificate','litellm-db-server-pki',ai);assert host in servercert['spec']['dnsNames'] and servercert['spec']['issuerRef']['name']=='platform-workload-ca'
pg=get('cluster','litellm-db',ai);primary=pg['status']['currentPrimary'];appsecret=get('secret','litellm-db-app',ai);password=base64.b64decode(appsecret['data']['password']).decode()
script='IFS= read -r PGPASSWORD; export PGPASSWORD; export PGSSLMODE=verify-full PGSSLROOTCERT=/controller/certificates/server-ca.crt; exec psql -h '+host+' -U litellm -d litellm -Atc "SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()"'
r=subprocess.run(['kubectl','-n',ai,'exec','-i',primary,'--','sh','-ec',script],input=password+'\n',capture_output=True,text=True,timeout=25);assert r.returncode==0 and r.stdout.strip()=='t'
e.record('database_client_trust_and_operator_namespace',{'database_namespace':ai,'operator_namespace':dbns,'ssl_verified':True})
with Forward(ai,'service/litellm',4000,14000) as llm:
 headers={'Authorization':'Bearer '+state['auth']['master-key']}
 _,readiness=llm.request('/health/readiness',headers=headers)
 _,models=llm.request('/models',headers=headers);assert any(m['id']=='validation-model' for m in models['data'])
 _,chat=llm.request('/chat/completions',{'model':'validation-model','messages':[{'role':'user','content':'namespace-test'}]},headers=headers)
 assert chat['choices'][0]['message']['content']=='proxy-route-verified'
e.record('real_database_backed_application_and_provider_route',{'reply':'proxy-route-verified','namespace':ai})
p=pod(demo,'app.kubernetes.io/name=application');uid=p['metadata']['uid'];cmd="import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080').read().decode())"
assert k('-n',demo,'exec',p['metadata']['name'],'-c','application','--','python','-c',cmd).strip()=='namespace-verified'
assert not any(v['name']=='openbao-auth' for c in p['spec']['containers'] if c['name']=='application' for v in c.get('volumeMounts',[]))
e.record('injected_agent_uses_configured_openbao_namespace',{'application_namespace':demo,'openbao_namespace':bao,'pod_uid':uid,'token_not_mounted_in_app':True})
# This Kustomization deliberately omits the namespace mapping. It must fail
# before applying its ConfigMap under StrictPostBuildSubstitutions.
negative={'apiVersion':'kustomize.toolkit.fluxcd.io/v1','kind':'Kustomization','metadata':{'name':'missing-namespace-test','namespace':'flux-system'},'spec':{'interval':'10m','path':'./flux/clusters/'+RUN+'/probes/missing','prune':True,'sourceRef':{'kind':'GitRepository','name':'flux-system'},'postBuild':{'substitute':{'substitution_enabled':'true'}}}}
r=subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(negative),capture_output=True,text=True,timeout=20);assert r.returncode==0
def rejected():
 obj=get('kustomization','missing-namespace-test','flux-system')
 return next((c for c in obj.get('status',{}).get('conditions',[]) if c['type']=='Ready' and c['status']=='False' and 'NS_AI' in c.get('message','')),False)
condition=wait('strict missing namespace rejected',rejected,90)
assert command(['kubectl','-n','flux-system','get','configmap','missing-namespace-must-not-exist'],False).returncode!=0
k('-n','flux-system','delete','kustomization','missing-namespace-test','--wait=false')
e.record('strict_controller_missing_namespace_rejected',{'reason':condition['reason'],'object_not_applied':True})
# Native interpolation is preserved in an actual Flux-applied resource.
literals=get('configmap','literal-interpolation-test','flux-system')['data'];assert literals=={'grafana':'${DS_PROMETHEUS}','otel':'${env:MY_POD_IP}','pod':'$(DATABASE_PASSWORD)'}
e.record('native_interpolation_preserved_by_controller')
allns={n['metadata']['name'] for n in json.loads(k('get','namespaces','-o','json'))['items']}
if MODE=='custom':
 for original in ['ai','secrets','certificates','observability','databases','demo']:assert original not in allns
for key in ['NS_AI','NS_SECRETS','NS_CERTIFICATES','NS_OBSERVABILITY','NS_DATABASES','NS_DEMO']:assert NS[key] in allns
assert 'proxy' not in allns and 'quality' not in allns
e.record('only_selected_namespaces_exist',{'selected':{key:NS[key] for key in ['NS_AI','NS_SECRETS','NS_CERTIFICATES','NS_OBSERVABILITY','NS_DATABASES','NS_DEMO']},'unused_namespace_bases_not_created':True,'legacy_defaults_absent':MODE=='custom'})
e.finish()
