# Grafana dashboard templates

These are `grafana.integreatly.org/v1beta1` **GrafanaDashboard custom resources**.
Grafana Operator owns reconciliation; no new CRD definitions are installed here.
The existing chart-supplied dashboards and category starter dashboards remain.

| Directory | Dashboard | Purpose |
| --- | --- | --- |
| `demo/` | Demo / SDK and workload health | Quote counter/rate, available replicas, CPU, memory and restarts |
| `platform/` | Platform / Capacity and pressure | Memory headroom/budgets, root disk capacity, pressure, Pending Pods, I/O wait |
| `platform/` | Platform / Scrape health | Up/down targets, scrape duration and sample volume by job |

Resources target namespace `observability`, Grafana instances with label
`dashboards: platform`, and datasource **VictoriaMetrics**, using Operator datasource
input substitution. Adapt these in an overlay for a different installation.
The lab includes this directory through its existing `dashboards` Kustomization,
which waits for the observability stack and its Grafana provisioning.

```sh
kustomize build flux/dashboards
kubectl apply --dry-run=server -k flux/dashboards
flux reconcile kustomization dashboards --timeout=5m
kubectl -n observability get grafanadashboards.grafana.integreatly.org
```

Check each CR's status for successful synchronization, then browse the dashboard
titles in Grafana. An accepted CR does not prove every query has live data.
The demo's `quotes` counter and dotted `service.name` resource label were verified
in the rebuilt lab. Other queries use kube-state-metrics, cAdvisor, node-exporter,
and standard scrape metrics supplied by the existing stack. No application
latency histogram, error counter, or Collector self-metrics is invented here.

No automatic demo traffic runs. Send quote requests using the
[verification runbook](../runbooks/operations/verify-platform.md), allow ingestion
time and choose a range containing traffic. Sparse counters can leave rate panels
empty. The cumulative quote panel resets with the service and is not an accounting
total. Logs and traces remain available in Explore; these dashboards don't add
cross-signal links or datasource configuration.

Memory budget sums omit init-container maxima and Pod overhead, so they are
approximate. Filesystem panels show the node root disk independently of Ceph.
Scrape failures deliberately remain visible; panels do not suppress the known
control-plane TLS issues.
