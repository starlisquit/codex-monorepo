#!/usr/bin/env python3
"""Check reusable declarative Flux wiring and real post-build substitution offline."""
from pathlib import Path
import os
import json
import subprocess
import tempfile
import yaml
from flux_render import build, substitute, example_variables, FLUX
flux=Path(__file__).resolve().parents[3];infra=flux/'infrastructure'
settings={**example_variables(),'CA_CERT_NAME':'tenant-root-key','CA_ISSUER_NAME':'tenant-workload-ca','CA_BUNDLE_NAME':'tenant-trust','CA_COMMON_NAME':'Tenant Validation Root','OBSERVABILITY_NAMESPACE':'tenant-metrics','CERTIFICATES_NAMESPACE':'tenant-pki','DATABASES_NAMESPACE':'tenant-data','LITELLM_NAMESPACE':'tenant-ai','QUALITY_NAMESPACE':'tenant-quality','SECRETS_NAMESPACE':'tenant-secrets','OPENBAO_AUTH_ROLE':'tenant-app-reader'}
entries=[]
for manifest in sorted(infra.rglob('deployment.yaml')):
 if '/opt-in/flux/' not in str(manifest):continue
 entries.extend(o for o in build(manifest.parent,settings) if o['apiVersion']=='kustomize.toolkit.fluxcd.io/v1' and o['kind']=='Kustomization')
by_name={o['metadata']['name']:o for o in entries};assert len(entries)==len(by_name),'Duplicate wiring-stage names'
seen=set()
def visit(name,chain):
 if name=='foundation' or name in seen:return
 assert name in by_name,('Unknown prerequisite',name)
 assert name not in chain,('Wiring cycle',chain+[name])
 for dep in by_name[name]['spec'].get('dependsOn',[]):visit(dep['name'],chain+[name])
 seen.add(name)
for name in by_name:visit(name,[])
for stage in entries:
 spec=stage['spec'];assert spec['postBuild']['substituteFrom']==[{'kind':'ConfigMap','name':'cluster-settings'}]
 objects=build(flux.parent/spec['path'].removeprefix('./'),settings)
 expected={(o['apiVersion'],o['kind'],o['metadata'].get('namespace',''),o['metadata']['name']) for o in objects if o['kind']=='HelmRelease' or (o['apiVersion']=='cert-manager.io/v1' and o['kind'] in ['Certificate','Issuer','ClusterIssuer']) or (o['apiVersion']=='postgresql.cnpg.io/v1' and o['kind']=='Cluster') or o['kind'] in ['Bundle','ClickHouseCluster','KeeperCluster']}
 actual={(h['apiVersion'],h['kind'],h.get('namespace',''),h['name']) for h in spec.get('healthChecks',[])}
 assert expected<=actual,('Missing readiness coverage',stage['metadata']['name'],expected-actual)
 for o in objects:
  if o['kind']=='Certificate' and o['spec']['issuerRef'].get('kind')=='ClusterIssuer':assert o['spec']['issuerRef']['name']=='tenant-workload-ca'
  if o['kind']=='ClusterIssuer':assert o['metadata']['name']=='tenant-workload-ca' and o['spec']['ca']['secretName']=='tenant-root-key'
  if o['kind']=='SecretStore':assert o['spec']['provider']['vault']['auth']['kubernetes']['role']=='tenant-app-reader'
  if o['kind']=='ConfigMap' and 'values.yaml' in o.get('data',{}):
   values=yaml.safe_load(o['data']['values.yaml'])
   if 'renovate' in values:
    cfg=json.loads(values['renovate']['config']);assert cfg['repositories']==['example/platform'] and cfg['platform']=='gitlab'
   assert 'platform-workload-ca' not in o['data']['values.yaml'],'Issuer was not substituted into chart values'
for owner,app in [('ai/litellm','litellm'),('quality/sonarqube','sonarqube')]:
 stages=build(infra/owner/'opt-in/postgresql/flux',settings);nodes={o['metadata']['name']:o for o in stages}
 assert {'name':app+'-db-integration'} in nodes[app]['spec']['dependsOn']
 assert {'name':app+'-db-certificates'} in nodes[app+'-db']['spec']['dependsOn']
 assert not nodes[app+'-db']['spec']['prune']
# Real Flux strict mode rejects missing settings instead of emitting empty identities.
missing=subprocess.run([FLUX,'envsubst','--strict'],input='name: ${REQUIRED_VALIDATION_MISSING}',text=True,capture_output=True)
assert missing.returncode!=0 and 'variable not set' in missing.stderr
assert '${DS_PROMETHEUS}' in substitute('value: $${DS_PROMETHEUS}',settings)
assert '${env:MY_POD_IP}' in substitute('value: $${env:MY_POD_IP}',settings)
print(f'Validated {len(entries)} reusable Flux stages: dependency DAG, readiness coverage, custom PKI/namespaces, strict settings and application-variable escaping')
