#!/usr/bin/env python3
"""Use native Flux envsubst for strict offline validation of the namespace contract."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import yaml

FLUX_ROOT = Path(__file__).resolve().parents[3]
DEFAULTS = yaml.safe_load((FLUX_ROOT / 'bootstrap/namespace-config/configmap.yaml').read_text())['data']
VARIABLE = re.compile(r'(?<!\$)\$\{([^}]+)\}')

def namespace_map(overrides=None):
    values = dict(DEFAULTS)
    profile = os.environ.get('NAMESPACE_PROFILE')
    if profile:
        values.update(yaml.safe_load(Path(profile).read_text()).get('data', {}))
    values.update(overrides or {})
    unknown = values.keys() - DEFAULTS.keys()
    if unknown:
        raise ValueError('Unknown namespace variables: ' + ', '.join(sorted(unknown)))
    for key, value in values.items():
        if not isinstance(value, str) or len(value) > 63 or not re.fullmatch(r'[a-z0-9](?:[-a-z0-9]*[a-z0-9])?', value):
            raise ValueError('Invalid namespace for ' + key)
        if value in {'flux-system', 'kube-system'}:
            raise ValueError('Bootstrap namespace is reserved: ' + value)
    if len(set(values.values())) != len(values):
        raise ValueError('Namespace groups must remain distinct; merging ownership is not supported')
    return values

def namespace_for(original):
    return namespace_map()[next(k for k, v in DEFAULTS.items() if v == original)]

def render(text, values=None):
    values = namespace_map() if values is None else values
    for expression in VARIABLE.findall(text):
        if expression not in DEFAULTS:
            raise ValueError('Only declared namespace variables may be substituted; escape literal ${' + expression + '} with $$')
    env = {k: v for k, v in os.environ.items() if not k.startswith('NS_')}
    env.update(values)
    return subprocess.check_output([os.environ.get('FLUX_BIN', 'flux'), 'envsubst', '--strict'], input=text, text=True, env=env)

def build(path, values=None):
    raw = subprocess.check_output([os.environ.get('KUSTOMIZE_BIN', 'kustomize'), 'build', str(path)], text=True)
    objects = [obj for obj in yaml.safe_load_all(raw) if obj]
    active = [obj for obj in objects if obj.get('metadata', {}).get('annotations', {}).get('kustomize.toolkit.fluxcd.io/substitute') != 'disabled']
    rendered = iter(obj for obj in yaml.safe_load_all(render(yaml.safe_dump_all(active, sort_keys=False), values)) if obj)
    return [obj if obj.get('metadata', {}).get('annotations', {}).get('kustomize.toolkit.fluxcd.io/substitute') == 'disabled' else next(rendered) for obj in objects]

def load_yaml(path, values=None):
    return yaml.safe_load(render(Path(path).read_text(), values))

def load_json(path, values=None):
    return json.loads(render(Path(path).read_text(), values))

def run_map(run):
    patch = Path(run) / 'flux-system/namespace-overrides.yaml'
    return namespace_map(yaml.safe_load(patch.read_text()).get('data', {}) if patch.exists() else {})

if __name__ == '__main__':
    for obj in build(sys.argv[1]):
        print(yaml.safe_dump(obj, sort_keys=False), end='---\n')
