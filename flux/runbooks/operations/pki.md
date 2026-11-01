# Central application PKI

Kubernetes/kubeadm PKI stays independent. cert-manager issues application
certificates from ClusterIssuer `platform-workload-ca`; trust-manager distributes
its public root as ConfigMap `platform-ca`, key `ca.crt`, in all namespaces.
The Bundle does not distribute private keys and is not automatically mounted or
trusted by every application. Existing HTTP endpoints remain HTTP.

## Bootstrap and migration

Root creation needs only cert-manager. Trust-manager's own certificate then uses
that root; the Bundle follows trust-manager. This separation avoids a bootstrap
cycle. The lab's full Cilium reconciliation follows the Bundle; initial Cilium
networking is still seeded before Flux by the existing bootstrap helper.

On this existing lab, BEFORE applying `pki/issuer`, run:

```sh
python3 flux/runbooks/scripts/adopt-openbao-ca.py
kubectl apply -k flux/infrastructure/certificates/pki/issuer
kubectl wait clusterissuer/platform-workload-ca --for=condition=Ready --timeout=3m
```

The helper adopts the previous OpenBao CA in memory, using stdin to create the
central Secret without printing or saving private keys. It refuses to overwrite
an existing central CA. The root Certificate keeps the existing key (Never
rotation policy), CA common name, and extends certificate validity to ten years.
This preserves signing identity for existing OpenBao clients. The historical
common name `openbao-injector-ca` is retained for that compatibility reason.
A fresh playground skips adoption and lets cert-manager generate its root key.

Private root material is in `certificates/platform-root-ca`; back it up outside
Git under approved key custody. This lab uses an online root. Production should
consider an offline root with an intermediate issuer instead. Never delete/recreate
this Secret as a routine renewal step. Root replacement needs an overlap trust
and leaf reissuance procedure; cert-manager CA issuers do not orchestrate that
migration automatically.

## Consumers

- OpenBao server/injector, Metrics Server and trust-manager use the central issuer.
- Hubble uses chart-native cert-manager certificates and the shared CA Bundle.
- Kyverno uses cert-manager-controlled intermediate CAs signed by the root, with
  its chart-supported namespaced leaf issuers.
- VictoriaMetrics Operator's webhook uses its chart-native cert-manager option.
- PostgreSQL server and replication leaf certificates use the central issuer;
  replication preserves the `streaming_replica` client identity. CNPG reload labels
  on generated Secrets let the operator observe renewal.

Migrating PostgreSQL's server CA requires external clients to trust the new root;
use `sslmode=verify-full` with the public Bundle. This migration does not change
password authentication to require TLS for every application connection.

The CloudNativePG operator's **own internal webhook PKI** and cert-manager's
bootstrap webhook PKI remain operator-managed. The pinned CNPG operator manages
its own CA/key format and serving-certificate lifecycle; replacing only its leaf
Secret would create competing reconcilers. These are explicit remaining exceptions,
not certificates falsely claimed to have migrated.

## Checks

```sh
kubectl get certificates,issuers,clusterissuers -A
kubectl get bundle platform-ca
kubectl get configmap platform-ca -A
kubectl -n observability wait apiservice/v1beta1.metrics.k8s.io --for=condition=Available --timeout=3m
kubectl top nodes
kubectl -n secrets get secretstore,externalsecret
kubectl -n databases get cluster application-db
```

Inspect public certificate chains and live TLS handshakes, not just Secret names.
Admission configuration changes require checking APIService/webhook CA injection
and representative server-side dry runs. Keep TLS verification enabled throughout.
The policy template `platform-pki-issuers` audits permitted Certificate issuer
references, including explicit bootstrap and Kyverno delegation exceptions. It
cannot prove a server loaded a certificate or that an HTTP connection uses TLS.
RBAC must separately protect issuers, signing keys and direct CertificateRequests.

NATS and Valkey also have central server certificates in `pki/brokers`. NATS
client port 4222 uses TLS and its cluster routes use verified peer TLS. NATS Box
trusts the public Bundle; its context uses `tls://nats.broker.svc:4222`.
Valkey uses TLS-only port 6379 (`port 0` disables its plaintext listener), with
TLS-aware probes and a CA-verifying exporter connection. Client certificates
are not required on these client-facing ports. NATS monitoring port 8222 and the
Valkey exporter scrape endpoint remain internal HTTP endpoints; this does not
claim HTTPS or mTLS everywhere.
