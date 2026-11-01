# Optional PostgreSQL for SonarQube

This directory deploys CloudNativePG Cluster `quality/sonarqube-postgresql`:
three PostgreSQL 18.6 instances, database/owner `sonarqube`, 20Gi ceph-block
storage per instance and no remote superuser access. CNPG generates the
`sonarqube-postgresql-app` credentials. cert-manager issues the server and
replication leaves through central `ClusterIssuer/platform-workload-ca`.
The shared CNPG operator installs its CRD once; this is a Cluster custom resource.

Select only the required namespace/source bases and the existing CNPG operator.
First select `certificates/` after the central issuer is Ready and wait for
both Certificates. Deploy this directory in a separate database Flux
Kustomization depending on that certificate stage, with prune:false and a
Cluster Ready health gate. Select the central trust Bundle so `platform-ca`
exists in namespace `quality`. Adjust storage/replicas before creation for the
actual environment. No database password is committed.

After the database is Ready, select `integration/` alongside the SonarQube
release. It creates optional watch-labelled ConfigMap
`quality/sonarqube-postgresql-values`. The base HelmRelease merges:

1. Shared defaults.
2. This PostgreSQL integration.
3. Optional cluster overrides.
4. Inline values, if present.

The integration points JDBC at the CNPG read/write service, uses the generated
application password, and enables sslmode=verify-full with the mounted public
CA. Only ca.crt is mounted; the CA signing key is not exposed to the application.
Retain that volume/mount if overriding chart lists. SonarQube performs its own
schema initialization/migration on startup; a separate migration Job is not added.

Provision the normal sonarqube-monitoring Secret outside Git. The generated app
Secret replaces the manually supplied sonarqube-database password for this mode.
Existing external database deployments can continue using the base template
without selecting either opt-in. Do not enable the integration before its
Cluster is Ready: an existing release watches the ConfigMap immediately.

The current run under clusters records a real Flux ordering example:
foundation -> CNPG operator -> PostgreSQL Ready -> SonarQube. The opt-in itself
contains no namespace definitions, operator installation or cluster-specific
Flux source settings. The focused run overrides storage to local-path/1Gi;
the shared default remains ceph-block/20Gi per database instance.

Database and SonarQube PVC backup/restore are separate requirements. This
opt-in does not configure an external bucket, WAL archiving or PITR. Preserve
credentials and data through upgrades and review PostgreSQL/SonarQube upgrade
compatibility before changing image versions.

See [verified findings](../../../../../docs/findings/sonarqube-postgresql-2026-11-01.md)
for the GitOps run, real analysis, browser and recovery results.

## Central PKI verification

`certificates/` owns cert-manager server and streaming-replication leaves, using
90-day lifetimes, 15-day renewal windows, rotating keys and `cnpg.io/reload`
Secret labels. The CNPG operator still manages its own bootstrap webhook PKI;
this integration centralizes the database server and replication certificates.

The integration mounts **only** public `ca.crt` from ConfigMap `platform-ca`,
not a CA signing key or a private server/replication leaf key. Keep this mount
when overriding Helm lists. Wait for public trust, leaf Certificates, then the
Cluster to be Ready before enabling the application integration.

[Central PKI runtime verification](../../../../../docs/findings/central-pki-postgresql-2026-11-01.md)
passed strict TLS and negative probes, app-backed writes, certificate hot renewal
and primary failover with two healthy instances in each focused test Cluster.
The default three-instance Ceph topology was not the lab topology. Existing
independent-CA deployments require a deliberate trust/issuer migration; the test
verified a fresh deployment and leaf renewal, not that in-place migration.
