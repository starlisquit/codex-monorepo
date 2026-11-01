# SonarQube

Select [this namespace base](../../namespaces/quality/kustomization.yaml) in foundation
or the deployment wrapper before this template. No all-namespaces bundle is
required; this directory does not create its own namespace.

Official [SonarSource chart](https://github.com/SonarSource/helm-chart-sonarqube),
chart `2026.5.1003`, from `https://SonarSource.github.io/helm-chart-sonarqube`.
This template explicitly selects Community Build `26.9.0.129388`; the chart's
Server application version is a different product/version. Developer/Enterprise
editions require their own configuration and license.

The component targets namespace `quality`. It is opt-in and not selected by the
full-platform overlay. Before selection, provision PostgreSQL with database and
dedicated login `sonarqube`, then adjust `jdbcOverwrite.jdbcUrl`/`jdbcUsername` to
match. The default hostname is `sonarqube-postgresql.quality.svc.cluster.local`.
The template does not install a database or grant database privileges. Its external
database avoids using SonarQube's embedded evaluation database.

Supply two same-namespace Secrets outside Git:

- `sonarqube-database`, key `password`: the dedicated database password.
- `sonarqube-monitoring`, key `passcode`: a strong, independent monitoring passcode.

For existing secure files:

```sh
kubectl create namespace quality --dry-run=client -o yaml | kubectl apply -f -
kubectl -n quality create secret generic sonarqube-database --from-file=password=/secure/database-password
kubectl -n quality create secret generic sonarqube-monitoring --from-file=passcode=/secure/monitoring-passcode
```

Provide a default StorageClass or override `persistence.storageClass`; the
SonarQube data volume requests 5 GiB. Database backups and persistent volumes
require separate recovery procedures. This lab-sized JVM configuration uses 512 MiB
heaps per web/compute/search process and a 4 GiB container limit; size for real
analysis workloads before production. Resource settings are not a throughput claim.

Upstream's sysctl init container is privileged and prepares Elasticsearch host
limits; the filesystem init container needs ownership-changing permissions.
Use a namespace/node policy that permits them, or prepare hosts independently and
disable those chart init containers deliberately. Inspect init-container results
and bootstrap logs instead of disabling Elasticsearch's bootstrap checks.

```sh
kustomize build flux/infrastructure/quality/sonarqube
helm repo add sonarqube https://SonarSource.github.io/helm-chart-sonarqube
helm pull sonarqube/sonarqube --version 2026.5.1003 --untar --untardir /tmp/sonarqube-chart
helm lint /tmp/sonarqube-chart/sonarqube -f flux/infrastructure/quality/sonarqube/values.yaml
helm upgrade --install sonarqube sonarqube/sonarqube --version 2026.5.1003 \
  -n quality -f flux/infrastructure/quality/sonarqube/values.yaml --wait --timeout 15m
kubectl -n quality port-forward svc/sonarqube-sonarqube 9000:9000
```

For Flux, select its source/component in the consuming overlay with a ready
database dependency and a HelmRelease health check. Do not manage the same release
with Helm CLI concurrently. Service access is internal HTTP by default; configure
your intended TLS ingress separately. Change the initial administrator password,
check `/api/system/status`, submit a real disposable analysis and verify its compute
task before calling validation complete. A Pod Ready check is insufficient.
