#!/usr/bin/env python3
"""Offline opt-in composition checks, including transformed selectors/references."""
from itertools import combinations
from pathlib import Path
import os
import subprocess
import tempfile
import yaml
from flux_render import build

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
print(f'Validated {count} opt-in compositions covering every {len(components)} Component; selectors, namespaces, ports, Gateway and RBAC references')
