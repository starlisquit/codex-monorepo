import hashlib,json,ssl,sys
from pathlib import Path
from datetime import datetime,timezone
from runtime import k,ready
run=Path(sys.argv[1]);contracts=json.loads((Path.home()/'contracts-evidence.json').read_text());applications=json.loads((Path.home()/'application-evidence.json').read_text());assert contracts['result']=='passed' and applications['result']=='passed'
def get(*args):return json.loads(k(*args,'-o','json'))
e={'contracts':contracts,'applications':applications,'captured_at':datetime.now(timezone.utc).isoformat(),'result':'passed'}
e['flux_path']=get('-n','flux-system','get','kustomization','flux-system')['spec']['path']
e['flux_stages']=[{'name':o['metadata']['name'],'revision':o.get('status',{}).get('lastAppliedRevision'),'ready':ready(o)} for o in get('-n','flux-system','get','kustomizations')['items']]
e['helm_releases']=[{'name':o['metadata']['name'],'namespace':o['metadata']['namespace'],'ready':ready(o),'chart_history':[{'chart':h.get('chartName'),'version':h.get('chartVersion'),'app_version':h.get('appVersion')} for h in o.get('status',{}).get('history',[])[:1]]} for o in get('get','helmreleases','-A')['items']]
assert all(o['ready'] for o in e['helm_releases'])
e['nodes']=[{'name':o['metadata']['name'],'version':o['status']['nodeInfo']['kubeletVersion']} for o in get('get','nodes')['items']]
e['root_ca_sha256']=hashlib.sha256(ssl.PEM_cert_to_DER_cert(get('-n','secrets','get','configmap','platform-ca')['data']['ca.crt'])).hexdigest()
namespaces={x['namespace'] for x in json.loads((run/'inventory.json').read_text())['credentials']}
e['workload_pods']=[]
for ns in namespaces:
 for o in get('-n',ns,'get','pods')['items']:
  if o['status']['phase']=='Succeeded':continue
  e['workload_pods'].append({'namespace':ns,'name':o['metadata']['name'],'uid':o['metadata']['uid'],'phase':o['status']['phase'],'ready':ready(o),'containers':[{'name':c['name'],'image':c['image']} for c in o['spec']['containers']]})
(Path.home()/'evidence.json').write_text(json.dumps(e,indent=2)+'\n');print('CAPTURED_SANITIZED_EVIDENCE')
