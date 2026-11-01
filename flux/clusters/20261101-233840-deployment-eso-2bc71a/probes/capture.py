"""Add public runtime metadata to sanitized test evidence."""
import hashlib,json,ssl,subprocess
from pathlib import Path
from datetime import datetime,timezone
def get(*args):return json.loads(subprocess.check_output(['kubectl',*args,'-o','json'],text=True))
p=Path.home()/'evidence.json';e=json.loads(p.read_text());assert e['result']=='passed'
e['captured_at']=datetime.now(timezone.utc).isoformat()
e['nodes']=[{'name':n['metadata']['name'],'version':n['status']['nodeInfo']['kubeletVersion']} for n in get('get','nodes')['items']]
e['helm_releases']=[{'name':r['metadata']['name'],'namespace':r['metadata']['namespace'],'chart':r['spec']['chart']['spec']['chart'],'version':r['spec']['chart']['spec']['version'],'ready':any(c['type']=='Ready' and c['status']=='True' for c in r.get('status',{}).get('conditions',[]))} for r in get('get','helmreleases','-A')['items']]
e['flux_path']=get('-n','flux-system','get','kustomization','flux-system')['spec']['path']
e['flux_stages']=[{'name':s['metadata']['name'],'revision':s.get('status',{}).get('lastAppliedRevision'),'ready':any(c['type']=='Ready' and c['status']=='True' for c in s.get('status',{}).get('conditions',[]))} for s in get('-n','flux-system','get','kustomizations')['items']]
assert all(h['ready'] for h in e['helm_releases']) and all(s['ready'] for s in e['flux_stages'])
ca=get('-n','demo','get','configmap','platform-ca')['data']['ca.crt']
e['root_ca_sha256']=hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca)).hexdigest()
e['application_pods']=[{'name':a['metadata']['name'],'uid':a['metadata']['uid'],'containers':[{'name':c['name'],'image':c['image']} for c in a['spec']['containers']],'service_account':a['spec']['serviceAccountName']} for a in get('-n','demo','get','pods')['items']]
p.write_text(json.dumps(e,indent=2)+'\n');print('CAPTURED_SANITIZED_EVIDENCE')
