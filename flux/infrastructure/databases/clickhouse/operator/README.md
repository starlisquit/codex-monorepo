# ClickHouse operator

Official [ClickHouse operator](https://github.com/ClickHouse/clickhouse-operator),
chart `oci://ghcr.io/clickhouse/clickhouse-operator-helm` version `0.0.8`
(app `v0.0.8`). Requires Kubernetes >=1.28 and cert-manager.

Select these independent bases in your cluster foundation:

- `infrastructure/namespaces/databases`
- `infrastructure/namespaces/certificates`
- `infrastructure/sources/clickhouse-operator`
- `infrastructure/sources/jetstack`

Deploy `infrastructure/certificates/cert-manager` and this operator template.
The HelmRelease waits for cert-manager. The shared cert-manager template enables
ServiceMonitor integration; satisfy its monitoring dependency or disable it in
a focused cluster. No monitoring stack is required by this operator template.

The operator watches all namespaces with cluster-wide RBAC by default. Override
chart values using optional `clickhouse-operator-cluster-values` ConfigMap in
`databases` (key `values.yaml`). No database cluster is created automatically. Select [`../cluster`](../cluster)
separately to create a ClickHouse cluster and its Keeper cluster.
Use `clickhouse.com/v1alpha1` `ClickHouseCluster` / `KeeperCluster` resources;
these differ from Altinity's ClickHouseInstallation API. CRDs are retained on
uninstall, so deleting the HelmRelease does not delete database resources.

The chart enables webhook and metrics TLS via cert-manager. ServiceMonitor is
disabled by default. Database storage, credentials, network access, TLS and
availability must be chosen for each consuming cluster. The single-replica
fixture in the validation run is deliberately non-HA and uses local-path storage.

See [validation findings](../../../../docs/findings/clickhouse-operator-2026-11-01.md).

## Central PKI

The chart now uses `ClusterIssuer/platform-workload-ca` explicitly for webhook
and metrics serving certificates. Provision the shared issuer before reconciling
this release; the cert-manager HelmRelease dependency alone does not gate the
ClusterIssuer's readiness. The chart no longer creates its self-signed Issuer.
Use `certManager.issuerRef` in cluster values only when deliberately selecting a
different authority. Kubernetes CA injection remains chart-native.

[Focused runtime verification](../../../../docs/findings/central-pki-network-2026-11-01.md)
passed verified TLS, wrong-CA/name rejection, admission and certificate renewal
with changed serving serials and no operator Pod restart. Database listener TLS
is a separate ClickHouseCluster setting and is not enabled by this operator option.
