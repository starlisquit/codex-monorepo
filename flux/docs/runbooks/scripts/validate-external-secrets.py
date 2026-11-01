#!/usr/bin/env python3
"""Validate opt-in credential ownership, backend isolation and composition offline."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import yaml
from namespace_support import build, load_yaml, load_json, namespace_for

flux = Path(__file__).resolve().parents[3]
infra = flux / 'infrastructure'
kustomize = os.environ.get('KUSTOMIZE_BIN', 'kustomize')
# Exact consumer contracts. CNPG and all PKI/controller-owned targets are excluded.
contracts = {
    'ai/litellm/opt-in/external-secrets': ('ai', {'litellm-auth': {'master-key', 'salt-key'}, 'litellm-provider-credentials': {'OPENAI_API_KEY'}}),
    'quality/sonarqube/opt-in/external-secrets': ('quality', {'sonarqube-monitoring': {'passcode'}}),
    'quality/sonarqube/opt-in/external-database-secrets': ('quality', {'sonarqube-database': {'password'}}),
    'ci/gitlab-runner/opt-in/external-secrets': ('ci', {'gitlab-runner-auth': {'runner-token', 'runner-registration-token'}}),
    'ci/renovate/opt-in/external-secrets': ('ci', {'renovate-credentials': {'RENOVATE_TOKEN'}}),
    'ui/redisinsight/opt-in/external-secrets': ('ui', {'redisinsight-encryption': {'key'}}),
    'ui/nui/opt-in/external-secrets': ('broker', {'nui-contexts': {'platform.json'}}),
    'databases/clickhouse/cluster/opt-in/external-secrets': ('databases', {'clickhouse-auth': {'password'}}),
    'backup/velero/opt-in/external-secrets': ('velero', {'velero-cloud-credentials': {'cloud'}}),
}

def compose(paths):
    with tempfile.TemporaryDirectory() as tmp:
        wrapper = Path(tmp)
        (wrapper / 'kustomization.yaml').write_text(yaml.safe_dump({
            'apiVersion': 'kustomize.config.k8s.io/v1beta1', 'kind': 'Kustomization',
            'resources': [os.path.relpath(p, wrapper) for p in paths]}))
        return build(wrapper)

def unique(objects):
    ids = [(o['apiVersion'], o['kind'], o['metadata'].get('namespace'), o['metadata']['name']) for o in objects]
    assert len(ids) == len(set(ids)), 'Duplicate composed resource identities'

# Discover new stores automatically; adding an integration requires an explicit consumer contract.
found = {str(p.parent.relative_to(infra)) for p in infra.rglob('secretstore.yaml')
         if (p.parent / 'role.json').exists()}
assert found == set(contracts), 'Credential opt-in contract coverage drift'
# Check contracts against actual consumer configuration, not just the opt-in files.
def values(relative):
    return load_yaml(infra / relative)

litellm_values = values('ai/litellm/values.yaml')
assert (litellm_values['masterkeySecretName'], litellm_values['masterkeySecretKey']) == ('litellm-auth', 'master-key')
assert litellm_values['environmentSecrets'] == ['litellm-provider-credentials']
assert litellm_values['proxy_config']['model_list'][0]['litellm_params']['api_key'] == 'os.environ/OPENAI_API_KEY'
salt = values('ai/litellm/opt-in/postgresql/integration/values.yaml')['extraEnvVars'][0]
assert salt['valueFrom']['secretKeyRef'] == {'name': 'litellm-auth', 'key': 'salt-key'}
sonar_values = values('quality/sonarqube/values.yaml')
assert (sonar_values['monitoringPasscodeSecretName'], sonar_values['monitoringPasscodeSecretKey']) == ('sonarqube-monitoring', 'passcode')
assert (sonar_values['jdbcOverwrite']['jdbcSecretName'], sonar_values['jdbcOverwrite']['jdbcSecretPasswordKey']) == ('sonarqube-database', 'password')
assert values('ci/gitlab-runner/values.yaml')['runners']['secret'] == 'gitlab-runner-auth'
assert values('ci/renovate/values.yaml')['existingSecret'] == 'renovate-credentials'
redis = list(yaml.safe_load_all((infra/'ui/redisinsight/redisinsight.yaml').read_text()))
redis_env = next(o for o in redis if o['kind'] == 'Deployment')['spec']['template']['spec']['containers'][0]['env']
assert next(e for e in redis_env if e['name'] == 'RI_ENCRYPTION_KEY')['valueFrom']['secretKeyRef'] == {'name': 'redisinsight-encryption', 'key': 'key'}
nui = values('ui/nui/values.yaml')['contextsVolume']
assert nui == {'name': 'nui-contexts', 'items': [{'key': 'platform.json', 'path': 'platform.json'}]}
clickhouse = list(yaml.safe_load_all((infra/'databases/clickhouse/cluster/cluster.yaml').read_text()))
assert next(o for o in clickhouse if o['kind'] == 'ClickHouseCluster')['spec']['settings']['defaultUserPassword']['secret'] == {'name': 'clickhouse-auth', 'key': 'password'}
assert values('backup/velero/opt-in/s3/values.example.yaml')['credentials']['existingSecret'] == 'velero-cloud-credentials'

original_namespaces = {key: value[0] for key, value in contracts.items()}
contracts = {key: (namespace_for(value[0]), value[1]) for key, value in contracts.items()}
all_resources = set()
targets = set()
for relative, (namespace, expected) in contracts.items():
    directory = infra / relative
    owner = directory.parent.parent
    objects = build(directory)
    assert {o['kind'] for o in objects} == {'ServiceAccount', 'SecretStore', 'ExternalSecret', 'ConfigMap'}
    assert all(o['metadata'].get('namespace') == namespace for o in objects)
    account, = [o for o in objects if o['kind'] == 'ServiceAccount']
    store, = [o for o in objects if o['kind'] == 'SecretStore']
    assert account['automountServiceAccountToken'] is False
    provider = store['spec']['provider']['vault']
    assert provider['server'] == 'https://openbao-active.' + namespace_for('secrets') + '.svc:8200'
    assert provider['path'] == 'kv' and provider['version'] == 'v2'
    assert provider['caProvider'] == {'type': 'ConfigMap', 'name': 'platform-ca', 'key': 'ca.crt'}
    auth = provider['auth']['kubernetes']
    assert auth['mountPath'] == 'kubernetes'
    assert auth['serviceAccountRef'] == {'name': account['metadata']['name'], 'audiences': ['openbao']}
    role = load_json(directory / 'role.json')
    assert role == {'bound_service_account_names': [account['metadata']['name']],
                    'bound_service_account_namespaces': [namespace], 'audience': 'openbao',
                    'token_policies': [auth['role']], 'token_no_default_policy': True,
                    'token_ttl': '15m', 'token_max_ttl': '1h'}
    descriptor, = [o for o in objects if o['kind'] == 'ConfigMap']
    assert descriptor['metadata']['name'] == store['metadata']['name'] + '-bootstrap'
    assert json.loads(descriptor['data']['role.json']) == role
    assert descriptor['data']['policy.hcl'] == (directory / 'policy.hcl').read_text()
    observed = {}
    paths = []
    for secret in [o for o in objects if o['kind'] == 'ExternalSecret']:
        spec = secret['spec']
        assert spec['refreshInterval'] == '1m'
        assert spec['secretStoreRef'] == {'kind': 'SecretStore', 'name': store['metadata']['name']}
        target = spec['target']
        assert target['creationPolicy'] == 'Owner' and target['deletionPolicy'] == 'Retain'
        identity = (namespace, target['name'])
        assert identity not in targets, 'Competing Secret owners'
        targets.add(identity)
        entries = spec['data']
        keys = {e['secretKey'] for e in entries}
        assert len(keys) == len(entries)
        assert all(set(e['remoteRef']) == {'key', 'property'} for e in entries)
        assert all(e['remoteRef']['property'] == e['secretKey'] for e in entries)
        for entry in entries:
            path = entry['remoteRef']['key']
            assert path.startswith('infrastructure/' + original_namespaces[relative] + '/')
            if path not in paths:
                paths.append(path)
        if target['name'] == 'gitlab-runner-auth':
            assert target['template'] == {'engineVersion': 'v2', 'data': {
                'runner-token': '{{ index . "runner-token" }}', 'runner-registration-token': ''}}
            keys = set(target['template']['data'])
        else:
            assert 'template' not in target
        observed[target['name']] = keys
    assert observed == expected, f'Consumer contract drift: {relative}'
    expected_policy = ''.join('path "kv/data/' + p + '" {\n  capabilities = ["read"]\n}\n' for p in paths)
    expected_policy += '\n# Only lifecycle operations on this client\'s own short-lived token.\npath "auth/token/lookup-self" {\n  capabilities = ["read"]\n}\npath "auth/token/renew-self" {\n  capabilities = ["update"]\n}\npath "auth/token/revoke-self" {\n  capabilities = ["update"]\n}\n'
    assert (directory / 'policy.hcl').read_text() == expected_policy, 'Policy differs from exact paths and self-token lifecycle scope'
    unique(compose([owner, directory]))
    all_resources.update([owner, directory])
unique(compose(sorted(all_resources)))
# Both common SonarQube modes compose; CNPG credentials never become ESO targets.
sonar = infra / 'quality/sonarqube'
unique(compose([sonar, sonar/'opt-in/external-secrets', sonar/'opt-in/postgresql', sonar/'opt-in/postgresql/integration']))
litellm = infra / 'ai/litellm'
unique(compose([litellm, litellm/'opt-in/external-secrets', litellm/'opt-in/postgresql', litellm/'opt-in/postgresql/integration']))
print(f'Validated {len(contracts)} OpenBao credential opt-ins and {len(targets)} Secret contracts; scoped policies, auth, trust, application and combined compositions')
