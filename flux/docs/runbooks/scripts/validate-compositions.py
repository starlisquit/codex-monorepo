#!/usr/bin/env python3
"""Offline opt-in composition checks, including transformed selectors/references."""
from itertools import combinations
from pathlib import Path
import os
import json
import subprocess
import tempfile
import yaml
from namespace_support import build, load_json, namespace_for


flux=Path(__file__).resolve().parents[3];infra=flux/'infrastructure'
kustomize=os.environ.get('KUSTOMIZE_BIN','kustomize')
def matches(selector,labels):return all(labels.get(k)==v for k,v in selector.items())
def check(objects):
 identities=[(o['apiVersion'],o['kind'],o['metadata'].get('namespace',''),o['metadata']['name']) for o in objects]
 assert len(set(identities))==len(identities),'Duplicate selected object identities'
 deployments=[o for o in objects if o['kind']=='Deployment'];services=[o for o in objects if o['kind']=='Service']
 for d in deployments:
  selector=d['spec']['selector']['matchLabels'];labels=d['spec']['template']['metadata']['labels'];assert matches(selector,labels)
  for container in d['spec']['template']['spec']['containers']:
   ports=[p['name'] for p in container.get('ports',[]) if 'name' in p];assert len(ports)==len(set(ports)),'Duplicate named container port'
 for monitor in [o for o in objects if o['kind'] in ['PodMonitor','ServiceMonitor']]:
  ns=monitor['metadata'].get('namespace','');selector=monitor['spec']['selector']['matchLabels'];app=monitor['metadata']['labels']['app.kubernetes.io/name']
  assert 'namespaceSelector' not in monitor['spec'],'Default monitors must remain namespace-scoped'
  if monitor['kind']=='PodMonitor':
   targets=[d for d in deployments if d['metadata'].get('namespace','')==ns and matches(selector,d['spec']['template']['metadata']['labels'])]
  else:
   selected=[s for s in services if s['metadata'].get('namespace','')==ns and matches(selector,s['metadata'].get('labels',{}))];assert len(selected)==1,'ServiceMonitor must select exactly its dedicated Service'
   svc=selected[0];assert svc['metadata']['name'].endswith('application-metrics')
   targets=[d for d in deployments if d['metadata'].get('namespace','')==ns and matches(svc['spec']['selector'],d['spec']['template']['metadata']['labels'])]
   port=monitor['spec']['endpoints'][0]['port'];sp=next(p for p in svc['spec']['ports'] if p['name']==port);assert sp['targetPort']=='metrics'
  assert len(targets)==1 and targets[0]['metadata']['labels']['app.kubernetes.io/name']==app,'Monitor selector leaked or matched no workload'
  endpoint=monitor['spec'].get('podMetricsEndpoints',monitor['spec'].get('endpoints'))[0]
  assert any(p['name']==endpoint['port'] for c in targets[0]['spec']['template']['spec']['containers'] for p in c.get('ports',[]))
 # Deployment credential Components must keep references correct after prefix/namespace transforms.
 stores={(o['metadata'].get('namespace',''),o['metadata']['name']):o for o in objects if o['kind']=='SecretStore'}
 external_secrets=[o for o in objects if o['kind']=='ExternalSecret']
 targets=set()
 for secret in external_secrets:
  ns=secret['metadata']['namespace'];spec=secret['spec'];name=secret['metadata']['name']
  assert spec['target']=={'name':name,'creationPolicy':'Owner','deletionPolicy':'Retain'}
  assert (ns,name) not in targets;targets.add((ns,name))
  store=stores[(ns,spec['secretStoreRef']['name'])];assert spec['secretStoreRef']['kind']=='SecretStore'
  vault=store['spec']['provider']['vault'];auth=vault['auth']['kubernetes'];sa=auth['serviceAccountRef']['name']
  assert vault['caProvider']=={'type':'ConfigMap','name':'platform-ca','key':'ca.crt'}
  assert vault['server']=='https://openbao-active.'+namespace_for('secrets')+'.svc:8200'
  assert auth['role']==sa and auth['serviceAccountRef']['audiences']==['openbao']
  assert any(o['kind']=='ServiceAccount' and o['metadata']['name']==sa and o['metadata']['namespace']==ns and o['automountServiceAccountToken'] is False for o in objects)
  consumers=[d for d in deployments if d['metadata']['namespace']==ns and any(e.get('secretRef',{}).get('name')==name for c in d['spec']['template']['spec']['containers'] for e in c.get('envFrom',[]))]
  assert len(consumers)==1,'ExternalSecret target must reach exactly its own app'
  app=consumers[0]['metadata']['labels']['app.kubernetes.io/name']
  assert spec['data']==[{'secretKey':'APP_PASSWORD','remoteRef':{'key':f'applications/{app}/environment','property':'APP_PASSWORD'}}]
 for d in deployments:
  pod=d['spec']['template'];annotations=pod['metadata'].get('annotations',{});spec=pod['spec']
  if annotations.get('vault.hashicorp.com/agent-inject')!='true':continue
  ns=d['metadata']['namespace'];sa=spec['serviceAccountName'];app=d['metadata']['labels']['app.kubernetes.io/name']
  assert annotations['vault.hashicorp.com/role']==sa,'Injector role must track renamed ServiceAccount'
  assert any(o['kind']=='ServiceAccount' and o['metadata']['name']==sa and o['metadata']['namespace']==ns and o['automountServiceAccountToken'] is False for o in objects)
  assert spec['automountServiceAccountToken'] is False
  assert annotations['vault.hashicorp.com/tls-skip-verify']=='false'
  assert annotations['vault.hashicorp.com/service']=='https://openbao-active.'+namespace_for('secrets')+'.svc:8200'
  assert annotations['vault.hashicorp.com/agent-inject-token']=='false'
  assert annotations['vault.hashicorp.com/agent-inject-containers']=='application'
  assert annotations['vault.hashicorp.com/agent-run-as-user']==str(spec['securityContext']['runAsUser'])
  assert annotations['vault.hashicorp.com/agent-run-as-group']==str(spec['securityContext']['runAsGroup'])
  assert annotations['vault.hashicorp.com/agent-inject-perms-config.json']=='0400'
  assert annotations['vault.hashicorp.com/agent-pre-populate-only']=='false'
  path=f'kv/data/applications/{app}/files'
  assert annotations['vault.hashicorp.com/agent-inject-secret-config.json']==path
  assert path in annotations['vault.hashicorp.com/agent-inject-template-config.json']
  volume=next(v for v in spec['volumes'] if v['name']==annotations['vault.hashicorp.com/agent-service-account-token-volume-name'])
  assert volume['projected']=={'defaultMode':292,'sources':[{'serviceAccountToken':{'path':'token','audience':'openbao','expirationSeconds':600}}]}
  assert not any(v['name']==volume['name'] for c in spec['containers'] for v in c.get('volumeMounts',[])),'Application must not mount agent login token'
 gateways={o['metadata']['name']:o for o in objects if o['kind']=='Gateway'}
 for g in gateways.values():assert len({l['name'] for l in g['spec']['listeners']})==len(g['spec']['listeners'])
 for route in [o for o in objects if o['kind'] in ['HTTPRoute','GRPCRoute','TLSRoute','TCPRoute','UDPRoute']]:
  for ref in route['spec']['parentRefs']:
   assert ref['name'] in gateways,'Renamed route parent reference is broken'
   listener=next(l for l in gateways[ref['name']]['spec']['listeners'] if l['name']==ref['sectionName'])
   assert route['kind'] in [k['kind'] for k in listener['allowedRoutes']['kinds']]
  for rule in route['spec']['rules']:
   for ref in rule['backendRefs']:
    svc=next(s for s in services if s['metadata']['name']==ref['name']);assert ref['port'] in [p['port'] for p in svc['spec']['ports']]
 accounts={o['metadata']['name']:o for o in objects if o['kind']=='ServiceAccount'};roles={o['metadata']['name']:o for o in objects if o['kind']=='ClusterRole'}
 for binding in [o for o in objects if o['kind'] in ['RoleBinding','ClusterRoleBinding']]:
  for subject in binding['subjects']:
   if subject['kind']=='ServiceAccount':
    assert subject['name'] in accounts,'Broken renamed RBAC subject'
    assert subject['namespace']==accounts[subject['name']]['metadata']['namespace'],'RBAC subject namespace was not transformed'
  if roles:assert binding['roleRef']['name'] in roles,'Broken renamed roleRef'
 for obj in objects:
  if obj['kind'] in ['ClusterRole','ClusterRoleBinding']:assert 'namespace' not in obj['metadata']

for mode, purpose in [('external-secrets','environment'),('openbao-injector','files')]:
 directory=infra/'primitives/deployment/opt-in'/mode
 role=load_json(directory/'role.example.json');identity='api-application-'+mode
 assert role=={'bound_service_account_names':[identity],'bound_service_account_namespaces':['demo'],'audience':'openbao','token_policies':[identity],'token_no_default_policy':True,'token_ttl':'15m','token_max_ttl':'1h'}
 policy=(directory/'policy.hcl').read_text()
 expected='path "kv/data/applications/application/'+purpose+'" {\n  capabilities = ["read"]\n}\n'
 expected+='\n# Only lifecycle operations on this client\'s own short-lived token.\n'
 for endpoint,capability in [('lookup-self','read'),('renew-self','update'),('revoke-self','update')]:
  expected+='path "auth/token/'+endpoint+'" {\n  capabilities = ["'+capability+'"]\n}\n'
 assert policy==expected,'Primitive policy example drift or excess scope'

components=sorted(p for p in infra.rglob('kustomization.yaml') if yaml.safe_load(p.read_text()).get('kind')=='Component')
owners={}
for manifest in components:
 owner=next((p for p in manifest.parents if (p/'kustomization.yaml').is_file() and yaml.safe_load((p/'kustomization.yaml').read_text()).get('kind')=='Kustomization'),None)
 if owner is None:raise SystemExit('No owning Kustomization for Component '+str(manifest))
 owners.setdefault(owner,[]).append(manifest.parent)
covered=set();count=0
for owner,opts in owners.items():
 selections=[combo for size in range(1,len(opts)+1) for combo in combinations(opts,size)] if len(opts)<=6 else [(p,) for p in opts]+[tuple(opts)]
 for combo in selections:
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);apps=['api','worker'] if owner.name=='deployment' else ['api']
   for app in apps:
    p=root/app;p.mkdir();wrapper={'apiVersion':'kustomize.config.k8s.io/v1beta1','kind':'Kustomization','resources':[os.path.relpath(owner,p)],'components':[os.path.relpath(c,p) for c in combo]}
    if 'primitives' in owner.parts:
     wrapper.update(namespace='composition-check',namePrefix=app+'-',labels=[{'pairs':{'app.kubernetes.io/name':app,'validation.example/owner':'composition'},'includeSelectors':True,'includeTemplates':True}])
    if owner.name=='deployment':
     names={c.name for c in combo};patches=[]
     if 'external-secrets' in names:
      patches.append({'target':{'kind':'ExternalSecret','name':'application-env'},'patch':yaml.safe_dump({'apiVersion':'external-secrets.io/v1','kind':'ExternalSecret','metadata':{'name':'application-env'},'spec':{'data':[{'secretKey':'APP_PASSWORD','remoteRef':{'key':f'applications/{app}/environment','property':'APP_PASSWORD'}}]}})})
     if 'openbao-injector' in names:
      path=f'kv/data/applications/{app}/files'
      patches.append({'target':{'kind':'Deployment','name':'application'},'patch':yaml.safe_dump({'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':'application'},'spec':{'template':{'metadata':{'annotations':{'vault.hashicorp.com/agent-inject-secret-config.json':path,'vault.hashicorp.com/agent-inject-template-config.json':'{{- with secret "'+path+'" -}}\n{{ .Data.data | toJSON }}\n{{- end -}}\n'}}}}})})
     if patches:wrapper['patches']=patches
    if owner.name=='gateway':
     svc={'apiVersion':'v1','kind':'Service','metadata':{'name':'application'},'spec':{'ports':[{'name':name,'port':port} for name,port in [('http',80),('grpc',50051),('tls',8443),('tcp',5432),('udp',5353)]]}}
     (p/'backend.yaml').write_text(yaml.safe_dump(svc));wrapper['resources'].append('backend.yaml')
    (p/'kustomization.yaml').write_text(yaml.safe_dump(wrapper,sort_keys=False))
   (root/'kustomization.yaml').write_text(yaml.safe_dump({'apiVersion':'kustomize.config.k8s.io/v1beta1','kind':'Kustomization','resources':apps}))
   objects=build(root)
   if 'primitives' in owner.parts:check(objects)
   if owner.name=='cilium':assert next(o for o in objects if o['kind']=='HelmRelease')['spec'].get('dependsOn') in [None,[]]
   covered.update(combo);count+=1
assert covered=={p.parent for p in components},'Some Components were skipped'
print(f'Validated {count} opt-in compositions covering every {len(components)} Component; selectors, namespaces, ports, Gateway, RBAC and credential references')
