"""Verify centralized Hubble/ClickHouse TLS, real RPC/admission and hot renewal."""
import base64,hashlib,json,os,ssl,subprocess,time
from pathlib import Path

def kube(*args):return subprocess.check_output(['kubectl',*args],text=True)
def get(kind,ns=None):return json.loads(kube('get',kind,*(['-n',ns] if ns else ['-A']),'-o','json'))
folder=Path('/home/laborant/.config/pki-validation');folder.mkdir(parents=True,exist_ok=True);folder.chmod(0o700)
ca=get('configmap/platform-ca','kube-system')['data']['ca.crt'];(folder/'ca.crt').write_text(ca);rootfp=hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca)).hexdigest()
def refresh_client():
 secret=get('secret/hubble-relay-client-certs','kube-system')['data']
 for key,name in [('tls.crt','client.crt'),('tls.key','client.key')]:p=folder/name;p.write_bytes(base64.b64decode(secret[key]));p.chmod(0o600)
refresh_client()
cmd=['/home/laborant/hubble','--server','tls://127.0.0.1:14245','--tls-ca-cert-files',str(folder/'ca.crt'),'--tls-client-cert-file',str(folder/'client.crt'),'--tls-client-key-file',str(folder/'client.key'),'--tls-server-name','hubble-relay.kube-system.svc']
def hubble():
 status=subprocess.check_output(cmd+['status'],text=True,timeout=15);assert 'Connected Nodes: 3/3' in status,status
 flows=subprocess.check_output(cmd+['observe','--last','3','--output','json'],text=True,timeout=15);rows=[json.loads(l) for l in flows.splitlines() if l.strip()];flows=[r for r in rows if 'flow' in r];assert flows
 return {'status':status.strip(),'flow_messages':len(flows),'flow_nodes':sorted({x.get('node_name',x.get('flow',{}).get('node_name','')) for x in flows})}
def admission():
 root=[]
 for kind in ['validatingwebhookconfigurations','mutatingwebhookconfigurations']:
  for o in get(kind)['items']:
   if 'clickhouse' not in o['metadata']['name']:continue
   for w in o['webhooks']:
    ca=base64.b64decode(w['clientConfig']['caBundle']).decode();fp=hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca)).hexdigest();assert fp==rootfp;root.append({'configuration':o['metadata']['name'],'webhook':w['name'],'ca_sha256':fp})
 assert len(root)>=2
 checks=[]
 for kind in ['KeeperCluster','ClickHouseCluster']:
  o={'apiVersion':'clickhouse.com/v1alpha1','kind':kind,'metadata':{'name':'pki-admission-validation','namespace':'databases'},'spec':{'replicas':1,'dataVolumeClaimSpec':{'resources':{'requests':{'storage':'1Gi'}}}}}
  if kind=='ClickHouseCluster':o['spec']['keeperClusterRef']={'name':'pki-admission-validation'}
  p=subprocess.run(['kubectl','create','--dry-run=server','-f','-'],input=json.dumps(o),text=True,capture_output=True);assert p.returncode==0,p.stderr;checks.append({'kind':kind,'dry_run':p.stdout.strip()})
 return {'webhook_ca_bundles':root,'server_dry_runs':checks}
targets=[{'name':'hubble-'+n,'host':'172.16.0.'+str(i+2),'port':4244,'server_name':n+'.default.hubble-grpc.cilium.io','client':True,'mtls':True} for i,n in enumerate(['cplane-01','node-01','node-02'])]+[{'name':'hubble-relay','host':'hubble-relay.kube-system.svc','port':443,'server_name':'hubble-relay.kube-system.svc','client':True,'mtls':True},{'name':'clickhouse-webhook','host':'clickhouse-operator-webhook-service.databases.svc','port':443,'server_name':'clickhouse-operator-webhook-service.databases.svc'},{'name':'clickhouse-metrics','host':'clickhouse-operator-metrics-service.databases.svc','port':8080,'server_name':'clickhouse-operator-metrics-service.databases.svc'}]
def tls():return json.loads(kube('exec','-n','kube-system','pki-probe','--','python','/scripts/verify-tls.py',json.dumps(targets)))
def pods():return {o['metadata']['name']:o['metadata']['uid'] for ns in ['kube-system','databases'] for o in get('pods',ns)['items'] if o['metadata']['name'].startswith(('cilium-','hubble-relay-','clickhouse-operator-'))}
def certificates():return [{'name':o['metadata']['name'],'namespace':o['metadata']['namespace'],'issuer':o['spec']['issuerRef'],'revision':o.get('status',{}).get('revision')} for o in get('certificates')['items']]
before={'tls':tls(),'hubble':hubble(),'admission':admission(),'pods':pods(),'certificates':certificates()};Path('/tmp/network-before.json').write_text(json.dumps(before,indent=2)+'\n')
for ns in ['kube-system','databases']:subprocess.run(['/home/laborant/cmctl','renew','--all','-n',ns],check=True)
old={x['name']:x['serial'] for x in before['tls']['results']};deadline=time.monotonic()+240
while time.monotonic()<deadline:
 try:
  aftertls=tls()
  if all(x['serial']!=old[x['name']] for x in aftertls['results']):break
 except subprocess.SubprocessError:pass
 time.sleep(5)
else:raise SystemExit('Not all serving certificates reloaded their renewed serial')
refresh_client();after={'tls':aftertls,'hubble':hubble(),'admission':admission(),'pods':pods(),'certificates':certificates()}
assert after['tls']['root_sha256']==before['tls']['root_sha256']==rootfp
assert before['pods']==after['pods'],'Unexpected workload restart during leaf renewal'
for cert in after['certificates']:
 if cert['name'].startswith(('hubble-','clickhouse-operator-')):assert cert['issuer']['name']=='platform-workload-ca' and cert['revision']>=2
out={'passed':True,'before':before,'after':after,'root_unchanged':True,'serving_serials_changed':True,'hot_reload_without_pod_restart':True};Path('/tmp/network-runtime-evidence.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':True,'tls_targets':len(targets),'hot_reload_without_pod_restart':True,'hubble_connected_nodes':'3/3','admission':True}),flush=True)
