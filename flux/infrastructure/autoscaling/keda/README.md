# KEDA autoscaling with VictoriaMetrics

KEDA chart `2.21.0` is pinned to the latest stable chart verified on 2026-11-01.
Reconcile the central namespace bundle first, then this directory after the
shared sources and monitoring CRD release. The HelmRelease reconciles when selected.

## Metrics integration

Two separate paths are configured:

- KEDA operator, metrics adapter, and admission-webhook metrics are exposed with
  ServiceMonitors. The VM operator converts them and VMAgent collects them.
- The excluded `opt-in/scaledobject/scaledobject.yaml.example` uses KEDA's Prometheus scaler to query
  the existing VMSingle Prometheus-compatible API. It does not require a separate
  Prometheus server or Prometheus Adapter.

To use the example, copy it to a `.yaml` file, replace the deployment name, metric
job selector, threshold, namespace, and replica bounds, and include it in a
workload's Kustomization. Keep the ScaledObject in the target workload's namespace.
The example is intentionally excluded from this operator Kustomization: no
workload is assigned an autoscaling policy by installing KEDA.

Use a query returning a single value and verify its behavior when data is absent.
The example uses `ignoreNullValues: "false"` to report missing data as a scaler
error. Choose scaling behavior for missing metrics deliberately. `minReplicaCount`
is one so the example does not scale a service to zero before its metric behavior
has been tested. Thresholds and query semantics must fit the selected workload.
Do not attach an independent HPA to the same deployment that KEDA manages.

The query URL assumes the existing VMSingle service name and namespace. Update it
if moving to VMCluster, VMAuth, or another endpoint. Use a TriggerAuthentication
and Secrets for authenticated endpoints; never put credentials in Git. Permit
operator egress to the VM endpoint (currently TCP 8428), API-server access to the
KEDA aggregated metrics API/webhook, and VMAgent access to KEDA metrics when
applying network policies.

KEDA installs its own external metrics adapter and APIService. Check that no other
adapter owns `external.metrics.k8s.io` before deployment. This is separate from
Kubernetes Metrics Server used for CPU/memory resource metrics; CPU/memory scalers
still need that resource-metrics capability.

After deployment, check all three ServiceMonitor targets, the external metrics
APIService, and the ScaledObject's Ready/Active conditions before testing scaling
on a real workload. No live scaling test has been performed here.

References:

- [KEDA charts](https://github.com/kedacore/charts)
- [Prometheus scaler](https://keda.sh/docs/latest/scalers/prometheus/)
