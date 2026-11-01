# Central PKI: LiteLLM and SonarQube PostgreSQL — 2026-11-01

Fresh K3s playground `6ae791fc46471e13268fb839`, Flux path
`./flux/clusters/20261101-222444-pki-databases-8fb839`, configuration revision
`c3d52c878f9f6c64bc4efbeb103d155ce308d005`. Evidence captured at 22:50:36
Europe/Istanbul (19:50:36 UTC). Focused topology: cert-manager/trust-manager,
monitoring CRDs, CNPG operator, two two-instance PostgreSQL clusters, LiteLLM,
SonarQube and an authenticated local OpenAI protocol fixture. No Ceph or full
observability stack was installed; database PVCs used local-path/1Gi.

## Changes and deployment order

Each application PostgreSQL opt-in now has a separate `certificates/` base.
It creates central-root-signed server and streaming-replication leaves with
explicit `ClusterIssuer/platform-workload-ca`, 90-day validity, 15-day renewal
window, rotating private keys and `cnpg.io/reload` Secret labels. The Cluster
references those server/client CA and TLS Secrets, replacing its independent
CNPG-managed database CA. cert-manager issues leaves; CNPG loads/reloads them.

The app integration mounts only `platform-ca` ConfigMap key `ca.crt`, distributed
by trust-manager. No root signing key or server/replication private leaf key is
mounted into either application. CNPG still generates the application password.

Flux gates the sequence: namespaces/sources -> cert-manager -> root issuer ->
trust-manager/public Bundle -> leaf Certificates -> PostgreSQL Ready -> app/DB
integration. The operator is installed separately and its own webhook PKI stays
operator-managed. This does not replace Kubernetes/bootstrap PKI.

## Verified behavior

- Both read/write Services completed TLS 1.3 handshakes against the public central
  root and expected DNS names. Wrong-CA and wrong-hostname probes were rejected.
- Authenticated application-user psql connections used `sslmode=verify-full`;
  both clusters wrote/read `central-ca-verified`, reported SSL/TLSv1.3 and had an
  active streaming replica. SQL probes used the existing public CA file under
  `/controller/certificates`; the database containers have read-only root filesystems.
- LiteLLM 1.106.6 migrations completed, readiness reported database connected,
  a generated virtual key was stored and reused, and a model request returned
  `proxy-route-verified` through the authenticated local fixture. No external
  model service or real provider credential was used.
- SonarQube Community Build 26.9.0.129388 started successfully with its strict JDBC
  URL, accepted an authenticated login, and created/retrieved project
  `central-pki-validation`. Lab credentials stayed outside Git.
- Renewed all four application server/replication leaves using cmctl v2.6.2.
  Both PostgreSQL serving serials changed; root fingerprint and database Pod UIDs
  stayed unchanged. SQL and both application round trips passed after hot reload.
- Deleted each cluster's original primary Pod. Both switched from instance 1 to
  instance 2, recovered to two healthy instances, and retained the SQL row,
  LiteLLM key and SonarQube project. Both applications reconnected successfully.
- Post-failover replication was `streaming`, TLSv1.3, with authenticated client DN
  `/CN=streaming_replica` in both clusters. Verified TLS, SQL and application checks
  passed again after failover.

[Sanitized before/renewal/failover evidence](evidence/central-pki-postgresql-2026-11-01.json)
contains only results, serials, public CA fingerprints, Pod identifiers and
certificate references. Reproduction scripts are retained in the run's `probes/`.

## Scope

The test used two replicas per database; shared defaults remain three instances
and Ceph-backed storage. This verifies fresh centralized deployment, certificate
renewal and database failover, not an unattended in-place migration from a
previous CA, backup/restore, load testing, a new Sonar analysis or browser suite.
The negative TLS checks exercise the serving endpoints; they are not separate
negative-test executions of Prisma/JDBC. Application success exercised the actual
configured Prisma/JDBC integrations with the central public trust bundle.

The root's historical common name `openbao-injector-ca` was preserved. The signing
backend is cert-manager's CA ClusterIssuer, not OpenBao's PKI engine. No root
private key was exported. Root replacement and existing-client trust overlap
remain separate migration procedures.

## Teardown

Findings and configuration were published to both remotes in commit
`b0375d1e7cce9a97e913d2d9ed1f2902ba6fc3b1` before the playground was
destroyed. A subsequent playground inventory at **22:59:35 Europe/Istanbul**
(19:59:35 UTC) confirmed no playgrounds remained, including this run and the
parallel networking and monitoring runs.
