#!/usr/bin/env python3
"""Exercise all shared templates with default/custom namespaces and strict failures."""
from pathlib import Path
import json
import os
import re
import subprocess
import tempfile
import yaml
from namespace_support import DEFAULTS, FLUX_ROOT, build, namespace_map, render, run_map

custom = namespace_map({key: 'test-' + value for key, value in DEFAULTS.items()})
paths = sorted(p.parent for category in ['infrastructure', 'policies', 'dashboards']
               for p in (FLUX_ROOT / category).rglob('kustomization.yaml')
               if yaml.safe_load(p.read_text())['kind'] == 'Kustomization')

def validate(objects, values):
    identities = [(o['apiVersion'], o['kind'], o['metadata'].get('namespace'), o['metadata']['name']) for o in objects]
    assert len(identities) == len(set(identities)), 'Duplicate identities after substitution'
    allowed = set(values.values()) | {'flux-system', 'kube-system'}
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ['namespace', 'targetNamespace', 'clusterResourceNamespace'] and isinstance(child, str) and child and '{{' not in child:
                    assert child in allowed, 'Namespace reference not in mapping: ' + child
                walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
        elif isinstance(value, str):
            assert not re.search(r'(?<!\$)\$\{NS_', value), 'Unresolved namespace placeholder'
            for key, old in DEFAULTS.items():
                if values[key] != old:
                    assert '.' + old + '.svc' not in value, 'Stale service DNS namespace: ' + old
    for obj in objects:
        if obj.get('metadata', {}).get('annotations', {}).get('kustomize.toolkit.fluxcd.io/substitute') == 'disabled':
            assert obj['kind'] == 'CustomResourceDefinition'
            continue
        walk(obj)
        if obj['kind'] == 'Namespace': assert obj['metadata']['name'] in allowed
        if obj['kind'] == 'ConfigMap' and 'role.json' in obj.get('data', {}):
            assert json.loads(obj['data']['role.json'])['bound_service_account_namespaces'] == [obj['metadata']['namespace']]
        if obj['kind'] == 'Certificate':
            for dns in obj['spec'].get('dnsNames', []):
                for key, old in DEFAULTS.items():
                    if values[key] != old: assert not dns.endswith('.' + old), 'Stale certificate SAN namespace'

for values in [namespace_map(), custom]:
    for path in paths: validate(build(path, values), values)

# These are literal application expressions after one Flux substitution pass.
assert '${env:MY_POD_IP}' in render((FLUX_ROOT/'infrastructure/demo/opentelemetry-demo/values.yaml').read_text())
assert '${DS_PROMETHEUS}' in str(build(FLUX_ROOT/'infrastructure/observability/dashboards/openbao'))
assert '$(DATABASE_PASSWORD)' in render((FLUX_ROOT/'infrastructure/ai/litellm/opt-in/postgresql/integration/values.yaml').read_text())
for bad in [{'NS_AI': ''}, {'NS_AI': 'Invalid_Name'}, {'NS_AI': 'flux-system'}, {'NS_AI': 'kube-system'}, {'NS_TYPO': 'valid'}, {'NS_AI': 'quality'}]:
    try: namespace_map(bad)
    except ValueError: pass
    else: raise AssertionError('Invalid mapping accepted: ' + str(bad))
for text in ['${DS_PROMETHEUS}', '${env:MY_POD_IP}', '${NS_TYPO}', '${NS_AI:=fallback}']:
    try: render(text)
    except ValueError: pass
    else: raise AssertionError('Unsafe placeholder accepted')
missing = namespace_map(); missing.pop('NS_AI')
try: render('${NS_AI}', missing)
except subprocess.CalledProcessError: pass
else: raise AssertionError('Missing namespace did not fail strict native substitution')

# Retained old runs are historical snapshots; new runs must bootstrap the map and
# apply the common substitution source to both root and child Flux objects.
new_runs = [p.parent for p in (FLUX_ROOT/'clusters').glob('*/flux-system/namespace-overrides.yaml')]
for run in [p.parent for p in new_runs]:
    objects = build(run, run_map(run))
    config, = [o for o in objects if o['kind']=='ConfigMap' and o['metadata']['name']=='cluster-namespaces']
    assert config['data'] == run_map(run)
    for obj in objects:
        if obj['apiVersion']=='kustomize.toolkit.fluxcd.io/v1' and obj['kind']=='Kustomization':
            assert obj['spec']['postBuild']=={'substituteFrom':[{'kind':'ConfigMap','name':'cluster-namespaces'}]}
    controller = next(o for o in objects if o['kind']=='Deployment' and o['metadata']['name']=='kustomize-controller')
    assert '--feature-gates=StrictPostBuildSubstitutions=true' in controller['spec']['template']['spec']['containers'][0]['args']

with tempfile.TemporaryDirectory() as tmp:
    profile=Path(tmp)/'profile.yaml';profile.write_text(yaml.safe_dump({'data':custom}))
    env=os.environ.copy();env['NAMESPACE_PROFILE']=str(profile)
    for script in ['validate-compositions.py','validate-external-secrets.py']:
        subprocess.run(['python3', str(Path(__file__).with_name(script))],env=env,check=True)
print(f'Validated {len(paths)} shared bases in default/custom profiles, {len(new_runs)} Flux bootstrap wirings, role bindings, DNS/SANs, interpolation preservation and invalid/missing namespace rejection')
