# Central application PKI

Reviewed **2026-11-02, Europe/Istanbul**. Central issuance is configured, and
focused tests have verified specific serving/client connections and renewals.
The [coverage inventory](../../architecture/pki-coverage.md) distinguishes those
results from integrations awaiting acceptance. The
[unfinished full-platform migration](../../findings/pki-last-run.md) is historical,
not a blanket description of the current focused verification. All referenced
validation playgrounds were destroyed after publication.

## Authority, key ownership and public trust

cert-manager's CA ClusterIssuer **`platform-workload-ca`** signs application leaves
**directly with the online root**, stored in `certificates/platform-root-ca`.
OpenBao is not this issuer; no OpenBao PKI engine, Vault Issuer or intermediate CA
is deployed. The root is the trust anchor/signing identity, not a serving leaf.

The namespaced self-signed Issuer `certificates/platform-root-bootstrap` creates
`Certificate/platform-root`. Declared settings: RSA 2048-bit, duration `87600h`,
renewBefore `8760h` and key rotationPolicy `Never`. The historical common name
`openbao-injector-ca` is retained; it does not identify a different current owner.
Verify actual issued validity/key identity rather than assuming desired duration
has already changed an existing certificate.

trust-manager's `platform-ca` Bundle reads only public `tls.crt` from the root
Secret and distributes `ConfigMap/platform-ca:ca.crt` to selected namespaces
(currently all). `kyverno-platform-ca` separately targets the public CA Secret
of that name only in namespace `kyverno`. Private keys are never Bundle targets.
Clients must explicitly select their CA file/Secret/configuration. A Bundle does
not enable HTTPS or automatically change application system trust.

## Fresh deployment order

Select only required namespace/source bases and workload stages in a **new run
folder**. The existing generator can create its initial Flux path; consumers
still add the selected workload and readiness stages.

1. Install cert-manager and any chart prerequisites, including monitoring CRDs
   when selected values require them. Its bootstrap webhook PKI stays independent.
2. Reconcile `infrastructure/certificates/pki/issuer`; wait for the root Certificate
   and ClusterIssuer to be Ready.
3. Reconcile trust-manager, whose serving Certificate uses the central issuer.
   Then reconcile required trust Bundles and confirm public trust reaches each
   consuming namespace. If selecting the Kyverno Bundle, configure its authorized
   public Secret target in trust-manager as supplied by the shared values.
4. Issue/wait for required server/client leaves, then install their consumers.
   Chart-generated cert-manager leaves can be created during that chart install;
   their issuer must already exist.
5. For LiteLLM/SonarQube CNPG opt-ins: select each `postgresql/certificates/` stage
   **before** the Cluster stage, wait for database readiness, then enable the
   application integration. Install the CNPG operator separately; its own webhook
   certificates remain operator-managed.
6. For Cilium/Hubble: seed CNI networking before Flux/PKI with Hubble disabled,
   then apply the final cert-manager integration after issuer/trust readiness.
   Relay serving TLS/mTLS needs an explicit consuming override; it is not enabled
   by the shared Hubble certificate settings alone.
7. OpenBao must have a centrally issued listener certificate and reachable verified
   HTTPS endpoint before ESO or injected agents authenticate to it. Provision KV,
   Kubernetes auth, application policies/roles and values separately; gate apps on
   their required SecretStores/ExternalSecrets being ready.

Do not make cert-manager/root/trust prerequisites depend on credentials available
only from OpenBao. OpenBao initialization/unseal/recovery material must also remain
outside that dependency cycle. Preserve server/client private keys only in the
containers/controllers that require them.

## Existing CA adoption is a separate migration

Fresh clusters **skip adoption** and let cert-manager generate a fresh root.
There is no live original lab CA to recover from the destroyed playgrounds.

For an existing cluster specifically using the legacy OpenBao CA, review backup,
client trust overlap and rollback before running the optional adoption helper
**before** installing `pki/issuer`:

```sh
python3 flux/docs/runbooks/scripts/adopt-openbao-ca.py
kubectl apply -k flux/infrastructure/certificates/pki/issuer
kubectl -n certificates wait certificate/platform-root --for=condition=Ready --timeout=3m
kubectl wait clusterissuer/platform-workload-ca --for=condition=Ready --timeout=3m
```

The helper copies the legacy `secrets/openbao-injector-ca` into the central Secret
through memory/stdin, without printing/saving private material, and leaves an
existing central CA unchanged. It is not a general root-replacement workflow.

In the historical adoption run, explicit root renewal was needed to apply the
longer declared validity. If appropriate for a reviewed migration, use
`cmctl renew platform-root -n certificates`, then compare the root revision,
actual expiry and unchanged public key. Reissuing a root certificate with the
same key still requires checking the trust material loaded by existing clients.
The historical identity-continuity check did not complete a full in-place
application migration.

Protect signing material and retain approved recovery copies independently of
Git and disposable VMs. Never delete/recreate `platform-root-ca` as a renewal
step. A CA Issuer does not orchestrate root replacement, trust overlap or all
leaf/client rollouts. An offline root/intermediate design is future work, not
the current architecture.

## Certificates versus application credentials

cert-manager owns central TLS Secrets and trust-manager owns public distribution.
OpenBao KV plus ESO owns only selected application password/API-token Secrets;
CNPG continues to generate its application database passwords. The separate
SonarQube external-database password opt-in is for a different deployment mode.
[Credential coverage](../../operations/application-external-secrets.md) has the
paths, scopes, ownership rules and live results.

The new application/Deployment ESO stores trust OpenBao with public
`ConfigMap/platform-ca`. The original lab-verification store in `secrets` still
selects the public `ca.crt` key of `openbao-server-tls`. That Secret also contains
the server private key; do not copy the whole Secret to application namespaces.

The shared OpenBao HelmRelease provides the injector's
`AGENT_INJECT_VAULT_CACERT_BYTES` from the server Secret's **public CA key only**.
The Deployment injector Component uses that trust, a dedicated service account
and an audience-bound projected token. Agents render files; this is not certificate
issuance, and successful token renewal/file refresh does not prove TLS leaf reload.
OpenBao's own leaf renewal/reload still requires a dedicated served-serial test.

## Acceptance and renewal checks

The following commands inspect status/public distribution without dumping private
Secrets. Run them only against the intended cluster/context and selected resources:

```sh
kubectl get certificates,issuers,clusterissuers -A
kubectl get bundles
kubectl get configmap platform-ca -A
kubectl get secretstores,externalsecrets -A
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
```

For each selected TLS connection:

1. Compare the live serving chain, expiry, issuer and expected DNS SANs against
   the public CA, not just Certificate Ready or a Secret name.
2. Verify positive application/admission operations and reject a wrong CA/name.
   Test missing-client-certificate/plaintext rejection only where enforcement is
   configured; server TLS does not imply mTLS.
3. Renew a leaf with cmctl, observe a changed **served serial**, then repeat the
   client/admission operations and check whether Pods restarted or hot-reloaded.
   Validate replication/probes/exporters separately where relevant.
4. For webhooks/APIService, check actual CA bundles and representative server-side
   dry runs. Disable any competing certificate writer before ownership handover.
5. Handle root changes separately, with trust overlap and explicit client rollout.

Most explicit broker/database leaves request duration `2160h`, renewBefore `360h` and
rotating keys; chart-issued lifetimes vary. Root key rotation is intentionally
`Never`. Secret updates alone do not prove a running process reloaded its key.
OpenBao's OnDelete StatefulSet also needs application-specific reload/rollout
acceptance; use readiness checks rather than assuming Deployment-style rollout.

## Evidence and remaining work

| Focused result | Verified scope |
| --- | --- |
| [Hubble / ClickHouse operator](../../findings/central-pki-network-2026-11-01.md) | Verified TLS 1.3, wrong CA/name rejection, Hubble mTLS/flows, admission, changed serving serials and hot reload; Relay serving TLS/mTLS was a run override |
| [LiteLLM / SonarQube CNPG](../../findings/central-pki-postgresql-2026-11-01.md) | Central server/replication TLS, strict client checks, real SQL/apps, hot renewal, primary failover and authenticated replication |
| [Deployment injector](../../findings/deployment-injector-runtime-2026-11-01.md) | Real admission, verified HTTPS to OpenBao, file delivery/refresh and token reauthentication; no TLS renewal test |
| [Infrastructure ESO](../../operations/application-external-secrets.md#validation-scope) | Nine opt-ins/ten Secret contracts with verified OpenBao access and real application use; not new serving TLS for those apps |

NATS/Valkey full TLS rollout/renewal, Kyverno stable handover, Rook dashboard served
chain/reload, generic `application-db` CA migration and remaining webhook renewal
suites are still open. The latest RedisInsight/NUI and Velero tests used isolated
fixtures, including local HTTP S3; they do not close platform broker TLS or
external-bucket trust checks. Metrics Server's kubelet connection remains distinct
from its own centrally signed serving endpoint; shared values do not disable
kubelet certificate verification.

Kubernetes PKI, cert-manager's bootstrap webhook and CNPG's operator webhook remain
independent. Internal HTTP endpoints remain HTTP unless explicitly configured
otherwise. There is no installed certificate-policy template enforcing issuer
selection: protect issuers, signing keys and CertificateRequests through RBAC.

The older network/PostgreSQL PKI run folders were removed; reports name the Git
revisions containing their original configs/probes. Reproduce from those revisions
or create a fresh focused run, publish findings to both remotes, then destroy it.
