# Application PKI coverage in the templates

This is a desired-configuration inventory, not a live audit. No playground is
running. The last migration did not complete end-to-end verification; see the
[last-run findings](../findings/pki-last-run.md).

**Not every bootstrapped application uses our CA.** Central certificate issuance,
public trust distribution and turning a plaintext listener into TLS are separate
operations. A Bundle does not make every client trust it automatically.

| Component / connection | Template configuration |
| --- | --- |
| OpenBao server and injector | Certificates from `platform-workload-ca`; server Secret mounted into TLS listener; injector CA injection configured |
| Metrics Server serving endpoint | Central ClusterIssuer, APIService CA injection and monitoring verification |
| Metrics Server to kubelets | Kubernetes/kubeadm certificates; lab overlay still uses `--kubelet-insecure-tls` (encrypted but unverified) |
| trust-manager serving endpoint | Certificate issuer patched to the central ClusterIssuer |
| Hubble server/relay client | Cilium chart's cert-manager integration and shared public CA Bundle |
| Kyverno webhooks | Central-root-signed leaves and public CA Secret from trust-manager; delegated chains are incompatible with the pinned admission readiness validator |
| VictoriaMetrics Operator webhook | Chart's cert-manager integration uses the central ClusterIssuer |
| NATS client and cluster endpoints | Central server/client-capable certificate; route peer verification configured; client-certificate enforcement not enabled on the client port |
| Valkey client endpoint | Central server certificate, TLS-only port and verified exporter connection configured; no client-certificate requirement |
| CNPG PostgreSQL server and replication | Central server/client leaf Certificates and Cluster references configured; last live reference update failed on an unavailable webhook |
| CNPG operator's own webhook | Operator-managed PKI; this is the CNPG exception, not its database endpoint |
| External Secrets webhook | Chart-native cert-manager Certificate uses the central issuer; chart certificate controller disabled to avoid competing writers |
| Rook/Ceph dashboard | RSA server Certificate from the central issuer, referenced through `cephClusterSpec.dashboard.sslCertificateRef` |
| cert-manager's own bootstrap webhook | Independently managed bootstrap CA; not migrated to the application issuer it must bootstrap |
| Kubernetes API, etcd, control-plane and kubelet identities | Existing Kubernetes/kubeadm PKI, intentionally independent |
| Grafana, Headlamp, Flux UI and most telemetry ingestion/query/metrics endpoints | Internal HTTP or plaintext protocol endpoints; no application serving certificate is configured |
| Tetragon | Local Unix-socket control interface, HTTP metrics; no new serving certificate |
| Trivy Operator | HTTP metrics; registry/database HTTPS uses its configured trust, not automatically our Bundle |
| Velero | HTTP metrics; object-store HTTPS trust is external-provider/default trust unless a BSL public CA reference is explicitly configured |

Additional operator-managed certificates must not be assumed to use the central
CA without an explicit integration and verification. This inventory does not
claim every default chart Secret or listener has been migrated. Kubernetes and
cert-manager bootstrap PKI and CNPG's operator webhook stay independently managed.

The certificate-policy template was removed. Certificate issuance alone does not
prove successful reload, client verification or plaintext rejection. Application
endpoint settings are unchanged: keeping internal HTTP was an explicit architecture
choice, and centralizing infrastructure certificates does not imply HTTPS everywhere.
