# Central application PKI

**Status:** desired configuration; the last live migration was stopped before
end-to-end acceptance and the playground was destroyed. Read the
[last-run findings](../../findings/pki-last-run.md) before deployment.

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
python3 flux/docs/runbooks/scripts/adopt-openbao-ca.py
kubectl apply -k flux/infrastructure/certificates/pki/issuer
kubectl wait clusterissuer/platform-workload-ca --for=condition=Ready --timeout=3m
```

The helper adopts the previous OpenBao CA in memory, using stdin to create the
central Secret without printing or saving private keys. It refuses to overwrite
an existing central CA. The root Certificate is configured to keep the existing key (Never
rotation policy) and CA common name, and requests ten-year certificate validity.
This preserves signing identity for existing OpenBao clients. In the recorded
run, an explicit renewal was needed to apply the longer duration after adoption;
with cmctl installed, use `cmctl renew platform-root -n certificates`, then check
its new revision, actual expiry and unchanged public key. The historical
common name `openbao-injector-ca` is retained for that compatibility reason.
A fresh playground skips adoption and lets cert-manager generate its root key.

Private root material is in `certificates/platform-root-ca`; back it up outside
Git under approved key custody. This lab uses an online root. Production should
consider an offline root with an intermediate issuer instead. Never delete/recreate
this Secret as a routine renewal step. Root replacement needs an overlap trust
and leaf reissuance procedure; cert-manager CA issuers do not orchestrate that
migration automatically.

## Consumers

See the [complete template coverage and exceptions](../../architecture/pki-coverage.md).

- OpenBao server/injector, Metrics Server and trust-manager use the central issuer.
- Hubble uses chart-native cert-manager certificates and the shared CA Bundle.
- Kyverno uses leaves signed directly by the central root. The pinned admission
  controller rejects a multi-certificate `tls.crt` during readiness validation;
  its chart's delegated CA produces precisely that chain. Helm post-rendering
  removes those delegated issuers/CAs, points both leaves at the central issuer,
  and sets both controllers' CA reference to public Secret `kyverno-platform-ca`.
  Their internal certificate writers remain disabled. Trust-manager distributes
  only the public root to that Secret, only in namespace `kyverno`. Its chart RBAC
  grants Secret read access across its target scope and write access restricted
  to that Secret name (creation cannot be name-restricted by Kubernetes RBAC).
- VictoriaMetrics Operator's webhook uses its chart-native cert-manager option.
- External Secrets uses the central issuer through its chart-native integration;
  its old certificate controller is disabled to avoid competing Secret writers.
- Rook's dashboard uses a central RSA TLS Secret through `sslCertificateRef`;
  `pki-ceph` gates the Ceph cluster on certificate readiness.
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
There is no certificate-policy template. RBAC must protect issuers, signing keys
and direct CertificateRequests. Application listener settings are unchanged by
these infrastructure issuer integrations.

The templates define NATS and Valkey central server certificates in `pki/brokers`. The intended NATS
client port 4222 uses TLS and its cluster routes use verified peer TLS. NATS Box
is configured to trust the public Bundle; its context uses `tls://nats.broker.svc:4222`.
Valkey is configured to use TLS-only port 6379 (`port 0` disables its plaintext listener), with
TLS-aware probes and a CA-verifying exporter connection. Client certificates
are not required on these client-facing ports. NATS monitoring port 8222 and the
Valkey exporter scrape endpoint remain internal HTTP endpoints; this does not
claim HTTPS or mTLS everywhere.


## Vault / OpenBao and our PKI

Yes: both support using externally issued PEM certificates for their HTTPS
listener through their native configuration. The issuer can be our cert-manager
ClusterIssuer; no custom Vault/OpenBao plugin is required for serving TLS.
It is not automatic discovery or automatic trust of our Bundle.

For the current OpenBao template, cert-manager produces `openbao-server-tls`;
the chart mounts it at `/openbao/tls`, and the listener already specifies:

```yaml
tls_disable: false
tls_cert_file: /openbao/tls/tls.crt
tls_key_file: /openbao/tls/tls.key
```

The injector has its own serving Certificate. External Secrets and monitoring
clients explicitly verify OpenBao with the configured CA. The same pattern can
be adapted to HashiCorp Vault's chart, using its chart-specific mount paths and
listener configuration. Configure DNS SANs for actual service/pod names, mount
private keys only into required containers, and verify certificate reload after
renewal. Kubernetes updating a Secret does not prove the process reloaded it.
Our retained OpenBao chart configuration requests the central issuer; the last
run did not complete renewed-serial and full handshake acceptance tests.

A TLS listener certificate is separate from the **PKI secrets engine**. If Vault
should issue certificates for the rest of the cluster, enable a PKI engine,
configure signing roles, give cert-manager scoped authentication, and use a
cert-manager Vault Issuer. To retain our root authority, Vault can own an
intermediate key and have its intermediate CSR signed by our root, then import
the signed chain. Do not copy the root private key into Vault merely to serve
HTTPS. This issuer-backend integration was not configured in the last run.

Avoid bootstrap cycles: Vault needs a listener certificate and reachable trusted
endpoint before a Vault-backed cert-manager Issuer can depend on it. Keep that
bootstrap issuer independent, or use an explicitly managed intermediate workflow.

## Renewal and access-control boundaries

The certificate-policy template was removed. Direct CertificateRequests,
signing-key access and issuer creation need RBAC controls; certificate issuance
is not itself TLS enforcement. For existing External Secrets installations,
verify its old certificate controller has stopped before cert-manager owns the
same Secret. Check CA injection and a representative webhook dry run. For Rook,
verify the dashboard's live certificate chain and renewed serial after a Secret
update; render success does not prove reload.

NATS/Valkey issuance was observed, but live TLS rollout was not verified. Before
another deployment, test NATS's rolling route-TLS transition without losing quorum,
NATS Box connectivity, Valkey plaintext rejection, exporter/probe CA verification,
and certificate reload after renewal. Server/client certificate issuance and
in-process reload are separate responsibilities. Single-instance Valkey may incur
a restart interruption. Internal monitoring endpoints remain HTTP by design.
