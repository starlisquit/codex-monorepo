import json,hashlib,ssl,sys
from pathlib import Path
from datetime import datetime,timezone
from runtime import *
from backend import NS
run=sys.argv[1];mode=sys.argv[2];e=json.loads((Path.home()/'application-evidence.json').read_text());assert e['result']=='passed'
def query(*args):return json.loads(k(*args,'-o','json'))
e['namespace_mapping']=NS;e['captured_at']=datetime.now(timezone.utc).isoformat()
e['flux_path']=query('-n','flux-system','get','kustomization','flux-system')['spec']['path']
e['flux_stages']=[{'name':o['metadata']['name'],'revision':o.get('status',{}).get('lastAppliedRevision'),'ready':ready(o)} for o in query('-n','flux-system','get','kustomizations')['items'] if o['metadata']['name']!='missing-namespace-test']
e['releases']=[{'name':o['metadata']['name'],'namespace':o['metadata']['namespace'],'ready':ready(o),'chart':o['status']['history'][0]['chartName'],'version':o['status']['history'][0]['chartVersion']} for o in query('get','helmreleases','-A')['items']]
assert all(x['ready'] for x in e['releases']) and all(x['ready'] for x in e['flux_stages'])
e['namespaces']=sorted(o['metadata']['name'] for o in query('get','namespaces')['items'])
e['nodes']=[{'name':o['metadata']['name'],'version':o['status']['nodeInfo']['kubeletVersion']} for o in query('get','nodes')['items']]
e['public_root_sha256']=hashlib.sha256(ssl.PEM_cert_to_DER_cert(query('-n',NS['NS_AI'],'get','configmap','platform-ca')['data']['ca.crt'])).hexdigest()
e['database_certificate']={'namespace':NS['NS_AI'],'dns_names':query('-n',NS['NS_AI'],'get','certificate','litellm-db-server-pki')['spec']['dnsNames']}
e['database_cluster']={'namespace':NS['NS_AI'],'instances':query('-n',NS['NS_AI'],'get','cluster','litellm-db')['status']['readyInstances']}
e['rendered_role_namespace']=json.loads(query('-n',NS['NS_AI'],'get','configmap','litellm-openbao-bootstrap')['data']['role.json'])['bound_service_account_namespaces']
(Path.home()/'evidence.json').write_text(json.dumps(e,indent=2)+'\n');print('CAPTURED_SANITIZED_EVIDENCE')
