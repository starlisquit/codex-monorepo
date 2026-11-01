# Trivy and Tetragon dashboards

Two `GrafanaDashboard` custom resources, reconciled by Grafana Operator into the
instance labelled `dashboards: platform` in `observability`. The parent dashboard
Kustomization includes them automatically. They use the chart's stable datasource
UIDs `VictoriaMetrics` (Prometheus API) and `VictoriaLogs` (native LogsQL plugin).
Change those UIDs in an overlay for a different Grafana deployment.

| Dashboard | Filters | Panels |
| --- | --- | --- |
| **Security / Trivy findings** | Namespace, workload kind, image repository, severity | Finding counts, represented reports/images, severity history, top namespaces/workloads/images, configuration, exposed-secret and RBAC summaries |
| **Security / Tetragon runtime** | Node, observed workload namespace/name | Agent coverage, event activity, top workloads, export throughput/age, losses/errors, process-cache health, raw runtime logs |

No extra CVE/binary label collection, scan policy, enforcement action, or scanner
configuration is enabled by these dashboards. Dependencies are the security
components' existing ServiceMonitors, the stack's kube-state-metrics, and vlagent
for runtime logs. They can be imported before those emit data, but empty panels
must not be interpreted as a healthy/clean result. The destroyed playground means
these dashboards are locally validated templates, not live ingestion results.

## Trivy interpretation

Metric names and labels are taken from Trivy Operator **v0.36.1** documentation
and collector source, matching the deployed chart's application version. Finding
metrics are **gauges backed by report CRs**, not counters: use their actual values,
not rate/increase. Vulnerabilities are summed across resource/container report
copies, so totals are not globally distinct CVEs. The image table uses a maximum
per image identity/severity before summing, reducing repeated report copies; it
still does not compute a union of CVE IDs.

Represented-image/report cards measure only what is present in metrics; they do
not establish completeness against all running images or report freshness. Check
operator logs, report/image identity, database freshness and scan Job outcomes.
Report expiry/workload changes can lower counts without a remediation. No missing
series are filled with a fake zero. Individual-CVE metrics are disabled in the
current operator template, so no unsupported CVE-detail panel is included.

Image finding panels follow all four filters. Configuration/Role summaries use
namespace and severity; ClusterRole summaries are global and use severity only.
Descriptions explain these differences. Findings from cluster-scoped RBAC cannot
be assigned to a selected namespace by simply filtering its label.

## Tetragon interpretation

Metric names/labels are from Tetragon **v1.8.0**'s metrics reference. Current
`metricsLabelFilter` retains namespace and workload, so those are the available
activity filters; binary/Pod label panels would not work without enabling more
labels. The pinned chart's ServiceMonitor adds the agent's `node` scrape label
and sets honorLabels=true, preserving observed workload namespace labels rather
than overwriting them with the collector namespace.

Observed events are normal process activity, not automatically attacks or policy
denials. Workload filters apply to event-activity panels. Export/error/cache panels
and runtime logs use node filtering; Ready/Desired agent cards are cluster-wide.
The exported/observed counts need not match due to export filters or lost events.
An old export timestamp can mean quiet/filtered workloads; some error counters
only exist after their first occurrence. No data is not proof of zero drops.
Loss counters describe different stages and are shown as separate series rather
than added together as distinct dropped events.

The log panel selects the `tetragon` stdout-exporter container. Its outer Kubernetes
labels identify the collector Pod, while nested event JSON identifies the observed
application. Therefore the workload namespace/name filters intentionally do not
filter raw logs. Rows stay single-line with inline labels hidden and details
expandable. Use the container-log-browser link for further investigation.

## Verify after bootstrap

```sh
kustomize build flux/dashboards/security
kubectl apply --dry-run=server -k flux/dashboards/security
flux reconcile kustomization dashboards --timeout=15m
kubectl -n observability get grafanadashboard security-trivy-overview security-tetragon-overview
```

Check DashboardSynchronized conditions and datasource UIDs, then browse both titles
in Grafana. Confirm real series for `trivy_image_vulnerabilities`,
`tetragon_events_total`, and `tetragon_events_exported_total` in Explore. Inspect
label values when dropdowns are empty, and verify the ServiceMonitors' targets.
Wait for a completed Trivy scan and generate a harmless exec in a test workload
before checking actual report/event panels. Confirm exported records reach
VictoriaLogs separately; a healthy scrape target does not establish log ingestion.

References:

- [Trivy metrics, v0.36.1](https://github.com/aquasecurity/trivy-operator/blob/v0.36.1/docs/tutorials/integrations/metrics.md)
- [Trivy collector, v0.36.1](https://github.com/aquasecurity/trivy-operator/blob/v0.36.1/pkg/metrics/collector.go)
- [Tetragon metrics, v1.8.0](https://github.com/cilium/tetragon/blob/v1.8.0/docs/content/en/docs/reference/metrics.md)
- [Tetragon event metrics, v1.8.0](https://github.com/cilium/tetragon/blob/v1.8.0/pkg/metrics/eventmetrics/eventmetrics.go)
