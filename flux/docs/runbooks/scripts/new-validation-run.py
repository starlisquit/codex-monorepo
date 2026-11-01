#!/usr/bin/env python3
"""Create a new, isolated Flux cluster folder for one playground run."""
import argparse
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import json
import yaml

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--name', required=True)
parser.add_argument('--play-id', required=True)
parser.add_argument('--namespace', action='append', default=[])
parser.add_argument('--source', action='append', default=[])
parser.add_argument('--created-at')
parser.add_argument('--git-url', required=True, help='This cluster repository URL, without credentials')
args = parser.parse_args()
for value in [args.name, args.play_id, *args.namespace, *args.source]:
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', value):
        parser.error('Names and playground IDs must be lowercase slugs')
url = urlsplit(args.git_url)
if url.scheme != 'https' or not url.netloc or url.username or url.password or url.query or url.fragment:
    parser.error('Use an HTTPS repository URL without credentials, query or fragment')
flux_root = Path(__file__).resolve().parents[3]
for category, values in [('namespaces', args.namespace), ('sources', args.source)]:
    for value in values:
        if not (flux_root / 'infrastructure' / category / value / 'kustomization.yaml').is_file():
            parser.error(f'Unknown {category} base: {value}')
created = datetime.fromisoformat(args.created_at.replace('Z', '+00:00')) if args.created_at else datetime.now(ZoneInfo('Europe/Istanbul'))
if created.tzinfo is None:
    parser.error('--created-at must include a timezone')
stamp = created.astimezone(ZoneInfo('Europe/Istanbul')).strftime('%Y%m%d-%H%M%S')
run = flux_root / 'clusters' / f'{stamp}-{args.name}-{args.play_id[-6:]}'
run.mkdir(parents=True, exist_ok=False)
(run / 'foundation').mkdir()
(run / 'flux-system').mkdir()
relative = run.relative_to(flux_root.parent).as_posix()
def write(path, documents):
    path.write_text(yaml.safe_dump_all(documents, sort_keys=False))
config = {'apiVersion': 'kustomize.config.k8s.io/v1beta1', 'kind': 'Kustomization'}
write(run / 'kustomization.yaml', [{**config, 'resources': ['flux-system', 'infrastructure.yaml']}])
write(run / 'foundation/kustomization.yaml', [{**config, 'resources': [f'../../../infrastructure/namespaces/{v}' for v in dict.fromkeys(args.namespace)] + [f'../../../infrastructure/sources/{v}' for v in dict.fromkeys(args.source)]}])
write(run / 'flux-system/kustomization.yaml', [{**config, 'resources': ['../../../bootstrap/flux-system', 'cluster-settings.yaml', 'gotk-sync.yaml']}])
write(run / 'flux-system/gotk-sync.yaml', [
    {'apiVersion': 'source.toolkit.fluxcd.io/v1', 'kind': 'GitRepository', 'metadata': {'name': 'flux-system', 'namespace': 'flux-system'}, 'spec': {'interval': '1m', 'url': args.git_url, 'ref': {'branch': 'main'}}},
    {'apiVersion': 'kustomize.toolkit.fluxcd.io/v1', 'kind': 'Kustomization', 'metadata': {'name': 'flux-system', 'namespace': 'flux-system'}, 'spec': {'interval': '1m', 'path': './' + relative, 'prune': True, 'sourceRef': {'kind': 'GitRepository', 'name': 'flux-system'}, 'postBuild': {'substituteFrom': [{'kind': 'ConfigMap', 'name': 'cluster-settings'}]}}}])
write(run / 'infrastructure.yaml', [{'apiVersion': 'kustomize.toolkit.fluxcd.io/v1', 'kind': 'Kustomization', 'metadata': {'name': 'foundation', 'namespace': 'flux-system'}, 'spec': {'interval': '1m', 'retryInterval': '20s', 'path': './' + relative + '/foundation', 'prune': True, 'sourceRef': {'kind': 'GitRepository', 'name': 'flux-system'}, 'wait': True, 'timeout': '5m'}}])
write(run / 'flux-system/cluster-settings.yaml', [{'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'cluster-settings', 'namespace': 'flux-system', 'labels': {'reconcile.fluxcd.io/watch': 'Enabled'}}, 'data': {'CLUSTER_NAME': args.name}}])
(run / 'run.json').write_text(json.dumps({'play_id': args.play_id, 'created_at': created.isoformat(), 'timezone': 'Europe/Istanbul', 'purpose': args.name, 'flux_path': './' + relative, 'status': 'preparing'}, indent=2) + '\n')
(run / 'README.md').write_text(f'# {args.name} validation run\n\nPlayground `{args.play_id}`. Flux reconciles only `./{relative}`.\nAdd only the workloads and readiness gates needed for this run. Keep credentials\noutside Git. Record findings, push both remotes, then destroy the playground.\nNever reuse this folder for a new playground.\n')
print(relative)
