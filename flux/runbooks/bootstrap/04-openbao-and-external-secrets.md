# 4. Initialize OpenBao and connect External Secrets

Use `dev-machine` as `laborant`. Prerequisites: healthy Ceph/CSI, issued server
and injector TLS Certificates, and the first OpenBao Pod running. The subsequent
replicas may not be created until their predecessor becomes Ready.

```sh
kubectl -n secrets get certificates.cert-manager.io
kubectl -n secrets get statefulset openbao
kubectl -n secrets get pods -l app.kubernetes.io/name=openbao
kubectl -n secrets exec openbao-0 -- bao status -format=json
```

A sealed server's status command returns a nonzero exit code; inspect its JSON.
Do not disable certificate verification: the chart sets `BAO_CACERT` and mounts
the trusted server CA.

## Initialize once and unseal

The helper initializes only Pod 0 if uninitialized, saves five shares and the root
token to an owner-only file, and unseals all three replicas with the same shares.
It refuses to overwrite existing material. On an existing initialized cluster,
recover the original material before running it. This file combines all recovery
material for a lab; use an approved independent custody process for production.

```sh
python3 flux/runbooks/scripts/initialize-openbao.py
stat -c '%a %n' /home/laborant/.config/codex-platform/openbao-init.json
kubectl -n secrets wait --for=jsonpath='{.status.readyReplicas}'=3 statefulset/openbao --timeout=5m
for pod in openbao-0 openbao-1 openbao-2; do
  kubectl -n secrets exec "$pod" -- bao status -format=json
done
```

Expected file permissions: 600. Do not `cat` the initialization file into a chat,
shared log, or issue. Securely retain it independently before losing the play.
Never initialize Pods 1 and 2 as separate clusters.

## Configure the backend and Git-managed store

```sh
python3 flux/runbooks/scripts/configure-openbao.py
flux reconcile kustomization openbao --timeout=3m
flux reconcile kustomization external-secrets --timeout=3m
flux reconcile kustomization secret-store --timeout=5m
kubectl -n secrets get secretstore,externalsecret
```

The helper uses a TLS-verified loopback port forward and reads the root credential
from the owner-only file without printing it. It configures KV v2 at `kv`,
Kubernetes auth, the scoped `external-secrets-lab` role/policy, and a non-sensitive
verification value. The Kubernetes auth role binds the expected service account,
namespace, and `openbao` audience. Git installs the corresponding SecretStore,
service account, token-review binding, and ExternalSecret.

Verify only the known non-sensitive marker, not arbitrary Secret contents:

```sh
kubectl -n secrets get secret openbao-verification \
  -o jsonpath='{.data.status}' | base64 -d
printf '\n'
```

Expected: `openbao-external-secrets-ok`, SecretStore Ready, and ExternalSecret
SecretSynced. The root token is not used as the External Secrets credential.

The auth/mount configuration lives in OpenBao's persistent data, not in the
SecretStore CR. Repeat configuration for a fresh cluster after initialization.
See [recovery](../recovery/openbao.md) for unsealing an existing cluster.

OpenBao uses an `OnDelete` StatefulSet. Use the ready-replica check above;
`kubectl rollout status statefulset/openbao` does not support this update strategy.
