# SonarQube PostgreSQL and per-run Flux validation — 2026-11-01

## Result

Added SonarQube's dedicated PostgreSQL opt-in and verified it through real Flux
reconciliation, a real scanner analysis, JDBC TLS tests, browser use and recovery.
No other recommended application/backend improvements were implemented.

The fixed iximiuz-labs and iximiuz-platform examples were deleted. This run uses
`flux/clusters/20261101-191654-sonarqube-postgresql-237f3e`, and the live root Flux
Kustomization points at that exact folder. The new run generator and repository
workflow require a new folder for each future playground, rather than reusing
an old example. Shared controller manifests are outside run folders.

## PostgreSQL opt-in

`infrastructure/quality/sonarqube/opt-in/postgresql` contains a CloudNativePG
Cluster custom resource: three PostgreSQL 18.6 instances, database/owner
sonarqube, 20Gi ceph-block per instance and remote superuser access disabled.
The operator installs the CRD once and generates application credentials and TLS.

The separately selected integration ConfigMap configures the generated app
Secret, CNPG read/write endpoint, JDBC sslmode=verify-full and the public CA
mount. Only ca.crt is exposed to the application, not the CA signing key. The
base SonarQube template still supports an existing external database when the
opt-in is not selected. Values merge in order: shared defaults, PostgreSQL
integration, cluster overrides, inline values.

## Run configuration and lifecycle

Playground `6ae765f67f32053bde237f3e` was created at 2026-11-01 19:16:54
Europe/Istanbul / 16:16:54 UTC. Only the required components were installed:
Flux 2.10.0 source/kustomize/helm controllers, the CNPG operator, PostgreSQL and
SonarQube, plus base K3s services. No Cilium migration, Ceph, monitoring stack,
other CI tools or unrelated application was deployed.

The run selects just quality/databases namespaces and cloudnative-pg/sonarqube
sources. Its four child Flux Kustomizations enforce:

`foundation -> cnpg-operator -> sonarqube-postgresql Ready -> sonarqube`.

The initial published configuration was `502553c`. All five live Flux
Kustomizations, including the root, became Ready at main@sha1:502553c2; both
HelmReleases became Ready. This is actual Git reconciliation, not a direct Helm
installation standing in for Flux. Public GitHub/main is the source; both Git
remotes were synchronized before bootstrap. No repository credential was needed.

Lab-only overrides are recorded in the run: local-path / 1Gi PVCs for all three
DB instances, a 1Gi SonarQube PVC and node-02 placement. The operator PodMonitor
is disabled and its monitoring-CRD dependency removed only in this focused run.
Shared defaults are unchanged. Monitoring/admin/scanner credentials were
provisioned outside Git; the administrator's default password was changed and
the scanner used a project-scoped token.

## Live checks

| Check | Observed result |
| --- | --- |
| Versions | CNPG chart 0.29.1; PostgreSQL 18.6; SonarSource chart 2026.5.1003 / Community 26.9.0.129388; Flux 2.10.0 |
| Database readiness | All three CNPG instances Ready before SonarQube stage applied |
| Application status | SonarQube API UP; HelmRelease and Flux application Kustomization Ready |
| Database/schema | 164 public application tables; sonarqube role is not superuser |
| JDBC encryption | 20 application-role connections observed with pg_stat_ssl.ssl = true |
| Driver trust | Using the application's actual PostgreSQL JDBC driver and credentials, an unrelated CA was rejected |
| Driver hostname verification | Correct CA with Service IP instead of the certificate DNS name was rejected |
| Scanner | Official scanner Job completed in 41 seconds; compute task SUCCESS |
| Persisted analysis | Analysis cfae026c-9f94-475f-92ad-8755014b3957, one Python file, three ncloc |
| Browser | Chromium login with changed password and project dashboard passed; no JavaScript errors or unexpected API errors |
| Recovery | SonarQube Pod and PG primary Pod deleted; CNPG promoted instance 2, original primary returned as replica, all three Ready |
| State continuity | Same analysis ID and measures, changed administrator password and browser dashboard retained after recovery |
| GitOps path | Live flux-system.spec.path matched the unique run folder; no old example path was used |

The scanner input is retained under the run's `validation/analysis-job.yaml`.
It is an explicit one-shot fixture, not part of the automatically reconciled
root Kustomization. It requires a project analysis token Secret provisioned
outside Git. Its 2Gi memory limit follows the previous scanner sizing finding;
no failed/low-memory retry was needed in this run.

Browser monitoring observed a 404 from alm_settings/get_binding for this
unbound disposable project. The API message explicitly said the project is not
bound to any DevOps Platform. That exact response was classified separately
rather than treating all 404s as acceptable. The dashboard worked, and no other
API errors or page exceptions occurred. No external ALM integration was added.

JDBC negative tests used a valid unrelated root CA and the Service IP to exercise
trust and DNS mismatch, using the same driver jar/connection settings as the
application. No TLS verification bypass was enabled. Expected driver rejection
logs are validation evidence, not an application startup failure.

[Sanitized evidence](evidence/sonarqube-postgresql-2026-11-01.json) records API
results, analysis/task IDs, Flux paths/revisions, Pod UIDs and the integration
values hash. The live ConfigMap hash matches the committed file.

## Future run workflow

`new-validation-run.py` creates a unique timestamp/purpose/play-ID folder and
self-pointing GitRepository/root Kustomization. It validates selected prerequisite
bases and rejects an existing folder instead of overwriting it. Use its real
playground ID, add only the required workload wrappers/gates, publish both
remotes, then call bootstrap-flux.sh with that explicit run path.

Bootstrap scripts no longer default to a fixed cluster example. Common pinned
Flux controller manifests are under bootstrap/flux-system. The validator now
discovers every saved run and checks its own sync path, local paths, dependency
cycles, selected namespaces/sources, duplicate ownership, HelmRelease health
coverage and PostgreSQL readiness checks. AGENTS.md preserves this workflow for
future runs. Completed folders remain as records and are never reused.

123 Kustomize builds passed. The current profile has four child definitions and
two selected releases; there is no hardcoded old 37-child/full-platform check.
The pinned SonarSource chart linted/rendered with final integration settings,
including public-only CA mount and generated password reference. Shell/Python
syntax and whitespace checks passed. The removed examples are absent from the
cluster directory; historical findings remain available as records.

## Limits

This controlled Pod-deletion test proves recovery and persisted analysis in the
lab, not uninterrupted availability, node/disk loss tolerance, production sizing
or RPO/RTO guarantees. SonarQube remains one application replica. No backup
bucket/WAL/PITR, restore exercise, ingress TLS or external ALM configuration was
validated. The database client link is verified TLS; the lab browser used a
private localhost port-forward. The current no-bucket constraint remains in
effect. Review stateful pruning and backups for a production installation.

## Publication and teardown

Findings and verified run configuration were published as `67bcb18` and both
remote main commit IDs were verified equal before teardown. The explicit
destroy API returned `ok: true` for `6ae765f67f32053bde237f3e` at
2026-11-01 19:43:03 Europe/Istanbul / 16:43:03 UTC. The playground was destroyed,
not stopped. The immediate listing reported it non-running during deletion
propagation; run.json records the completed/destroyed state.
