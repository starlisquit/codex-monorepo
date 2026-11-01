# OpenBao unseal and recovery boundaries

After Pod or VM restarts, manually sealed servers may need unsealing again.
The original Raft data and original unseal material must belong to the same
cluster. Do not initialize a new cluster as a substitute for finding lost keys.

From `dev-machine`, with the original owner-only initialization file restored:

```sh
stat -c '%a %n' /home/laborant/.config/codex-platform/openbao-init.json
for pod in openbao-0 openbao-1 openbao-2; do
  kubectl -n secrets exec "$pod" -- bao status -format=json
done
python3 flux/docs/runbooks/scripts/initialize-openbao.py
kubectl -n secrets wait --for=jsonpath='{.status.readyReplicas}'=3 statefulset/openbao --timeout=5m
kubectl -n secrets get secretstore,externalsecret
```

The helper skips initialization when the first server is already initialized and
uses the original shares to unseal replicas. If the first server is uninitialized
but an initialization file already exists, it refuses to overwrite that material.
Stop and establish whether the PVC, data directory, or cluster identity changed.

If the servers are unsealed but External Secrets fails, inspect SecretStore
conditions, server certificate trust, service-account namespace/audience, role
bindings, and the OpenBao auth mount/policy. Do not replace short-lived Kubernetes
authentication with a root-token Kubernetes Secret as a shortcut.

A true disaster-recovery procedure needs an independently retained Raft snapshot,
original recovery/unseal material, version-compatible restore instructions, and a
restore test. None of those are proven by having three Ready Pods. Off-cluster
snapshot backup and restore were not configured or tested in this lab.
