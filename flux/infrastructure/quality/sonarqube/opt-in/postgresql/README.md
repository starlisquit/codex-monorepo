# Optional PostgreSQL for SonarQube

This directory deploys CloudNativePG Cluster `quality/sonarqube-postgresql`:
three PostgreSQL 18.6 instances, database/owner `sonarqube`, 20Gi ceph-block
storage per instance and no remote superuser access. CNPG generates the
`sonarqube-postgresql-app` credentials and `sonarqube-postgresql-ca` TLS material.
The shared CNPG operator installs its CRD once; this is a Cluster custom resource.

Select only the required namespace/source bases and the existing CNPG operator.
Deploy this directory in a database Flux Kustomization with prune:false and a
Cluster Ready health gate. Adjust storage/replicas before creation for the
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
