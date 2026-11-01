# Grafana datasource definitions

Define additional `grafana.integreatly.org/v1beta1` GrafanaDatasource custom
resources here. The parent dashboard build includes this directory. Its initial
`resources: []` deliberately selects no incomplete examples: configure a datasource
and add its filename to that list when its prerequisites exist. No suspension
flag is needed. Backend credentials cannot be invented by a shared template.

The existing VictoriaMetrics chart retains ownership of its default metrics,
logs, traces and Alertmanager datasources. Use unique resource names, datasource
names and UIDs so custom definitions do not compete with those. The older empty
`infrastructure/observability/datasources/` directory remains available for existing
consumers; new definitions can live here without changing chart-owned resources.

## PostgreSQL example

`postgres.yaml` uses Grafana's built-in PostgreSQL plugin and targets the current
CNPG Service `application-db-rw.databases.svc.cluster.local:5432`, database
`application`. Adapt these for another backend. It selects the existing Grafana
instance labelled `dashboards: platform` and keeps the default datasource unchanged.
Its stable UID is `application-postgres`, which dashboards can reference.

Create a dedicated, least-privilege **read-only** database login and grant only
required schema/table access. Do not reuse the CNPG owner or PostgreSQL superuser.
Grafana does not restrict arbitrary SQL submitted through the datasource: database
privileges are the enforcement boundary. Configure default table privileges if
future tables should be readable. This resource does not create a database/role
or grant SQL permissions.

Provision Secret `observability/grafana-postgres-credentials` with keys `username`
and `password` through External Secrets or another approved secret workflow.
For preexisting local files outside Git:

```sh
kubectl -n observability create secret generic grafana-postgres-credentials \
  --from-file=username=/secure/path/to/grafana-postgres-username \
  --from-file=password=/secure/path/to/grafana-postgres-password
```

Use files containing the exact values, without trailing newlines. Do not commit
credential files or Secret manifests containing their values.

The template uses `sslmode: verify-full`, Grafana's file-content TLS configuration,
and public CA material from ConfigMap `observability/platform-ca`, key `ca.crt`.
That ConfigMap is distributed by trust-manager in this repo's PKI configuration.
Confirm the PostgreSQL server actually uses a matching issued certificate; the
last live migration did not complete. For another database CA, change the reference.
A hostname matching a certificate DNS SAN is required. No CA signing key or TLS
client key is referenced; this is server TLS plus password authentication, not mTLS.

Grafana Operator `valuesFrom` substitutes `$username`, `$password` and `$ca.crt`
using their referenced key names. These are operator placeholders, not literal
credentials or environment variables inside Grafana. The unbraced form also avoids
Flux's `${...}` post-build substitution. The password and CA content are placed in
Grafana's secure datasource configuration. Both referenced objects must be in the
same namespace as the GrafanaDatasource.

After provisioning the role, Secret, trust and any required network allows, select
it in this directory's `kustomization.yaml`:

```yaml
resources:
- postgres.yaml
```

Commit and push that selection, then:

```sh
kustomize build flux/dashboards/datasources
kubectl apply --dry-run=server -f flux/dashboards/datasources/postgres.yaml
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization dashboards --timeout=15m
kubectl -n observability get grafanadatasource application-postgres -o yaml
```

Check the Operator synchronization conditions and Grafana's **Save & test** or
an actual read-only SQL query. An accepted resource alone does not prove password,
TLS trust, network reachability or SQL permissions. Grafana's Pod needs egress and
the database needs ingress on TCP 5432 if isolated by NetworkPolicy. A NetworkPolicy
allow does not supply SQL authorization. Connection-pool defaults are explicit
and can be adapted to the database's connection budget.

The template was checked against the pinned Grafana Operator CRD schema. No live
PostgreSQL datasource connection was tested because the playground is destroyed.
