# Additional Grafana datasources

Grafana Operator supports `GrafanaDatasource` custom resources using
`grafana.integreatly.org/v1beta1`. The operator installs their CRD; define instances
of that resource here rather than another copy of the CRD schema.

The VictoriaMetrics chart continues to manage its default datasources. This folder
is for additional datasources, each with a unique resource name, datasource name,
and datasource UID to avoid conflicting with those defaults.

To add a datasource:

1. Copy `opt-in/prometheus/prometheus.yaml.example` to a descriptive `.yaml` filename.
2. Replace the placeholder URL, names, and UID; choose the appropriate Grafana
   datasource type and settings for your backend. Keep `isDefault: false` unless
   deliberately changing which datasource is the default.
3. Keep `instanceSelector.matchLabels.dashboards: platform` to select the existing
   bundled Grafana through its operator binding. Resources belong in `observability`.
4. Add the filename to `resources` in this directory's `kustomization.yaml`.
5. Reconcile this directory through a Flux Kustomization that depends on the ready
   Grafana Operator and VictoriaMetrics stack. The stack creates the Grafana binding.

The example is excluded from reconciliation and references a reserved `.invalid`
address. There are no active datasource resources in this folder initially.

For authentication, use the operator's Secret-backed datasource configuration;
never commit credential values. Nonstandard datasource plugins must also be
available in Grafana; configure them according to the operator's supported plugin
configuration and the datasource's requirements.

Validate with `kustomize build flux/infrastructure/observability/datasources`.

New definitions can also use [flux/dashboards/datasources](../../../dashboards/datasources/README.md),
which includes a PostgreSQL example. Keep each datasource owned by one location.
