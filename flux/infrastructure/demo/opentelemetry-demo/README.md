# Minimal OpenTelemetry demo through native Victoria agents

The shared template now enables only **currency** and **quote**, plus one small
Collector. All other pinned-chart demo components are explicitly disabled,
including the browser load generator, Kafka, storefront, AI services, flagd,
OpAMP server, and the demo databases. This is the shared default, not just a lab
override. The chart remains pinned to `0.42.6` (application `3.1.0`).

| Workload | Role | CPU request | Memory request | Memory limit |
| --- | --- | ---: | ---: | ---: |
| currency | Standalone C++ gRPC service | 10m | 32Mi | 64Mi |
| quote | Standalone instrumented PHP HTTP service | 10m | 48Mi | 96Mi |
| otel-collector | OTLP compatibility/forwarding bridge | 25m | 96Mi | 192Mi |

Total requests: **45m CPU and 176Mi memory**; memory limits total 352Mi.
The previous live demo requested about 5.1 GiB. These are requested resources,
not a guarantee of actual usage or proof that the entire platform now fits.

## Telemetry paths

```text
currency (OTLP/gRPC) and quote (OTLP/HTTP)
  -> Collector
     -> VMAgent :8429 -> VictoriaMetrics
     -> VLAgent :9429 -> VictoriaLogs
     -> VTAgent :10429 -> VictoriaTraces
```

The Collector remains because the C++ service's SDKs use gRPC and the native
agents accept HTTP/protobuf. It has only the OTLP receiver, memory limiter,
batching, health check, and three native-agent exporters. It does not scrape
removed Kafka/ad services, watch Kubernetes objects, connect to OpAMP, collect
host metrics, or convert spans into metrics.

The explicit `alternateConfig` also avoids the Helm 4 null-pipeline merge failure
seen during the full-demo rollout. When changing chart versions, compare upstream
defaults and explicitly review this configuration. Both shared and lab renders
are checked to contain exactly these three workload controllers.

The demo's bundled Prometheus, Grafana, Jaeger, OpenSearch, and eBPF profiler stay
disabled. Existing observability services supply storage and visualization.
VLAgent receives SDK logs in push mode; it does not tail container stdout/stderr.

## Enable and generate a small amount of traffic

The HelmRelease reconciles when included. The full platform overlay
orders it after the observability stack and traces agent are ready, and
requires all three workloads to run on workers.

There is **no automatic load generator**. To exercise quote, forward its Service:

```sh
kubectl -n demo port-forward service/quote 8080:8080
```

In another terminal:

```sh
curl -fsS -H 'Content-Type: application/json' \
  --data '{"numberOfItems":2}' http://127.0.0.1:8080/getquote
```

Expected response: `17.98`. The pinned quote implementation emits a manual `quotes`
counter, a calculation span, and an SDK log for this request. Give periodic metric
export time to flush, then look for recent `service.name=quote` data in Grafana
Explore's VictoriaMetrics, VictoriaLogs (DS), and VictoriaTraces datasources.
Actual ingestion must be verified; rendering alone does not prove it.

Currency exposes its gRPC API on the `currency` Service, port 8080. It does not
require Kafka, the storefront, flagd, or a database to start.

## Validation and rollout

```sh
kustomize build flux/infrastructure/demo/opentelemetry-demo
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization otel-demo --timeout=15m
kubectl -n demo get deployments,pods
kubectl -n demo logs deployment/otel-collector --tail=100
```

Expect only currency, quote, and otel-collector workload controllers after the
Helm upgrade removes the disabled components. Pending/failed old releases and
unready Flux dependencies can delay application of a Git change; inspect their
status rather than assuming a push already removed running Pods.

See [resource findings](../../../docs/findings/resource-pressure.md),
[Helm findings](../../../docs/findings/flux-and-helm.md), and the
[verification runbook](../../../runbooks/operations/verify-platform.md).

References: [pinned demo chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-demo),
[quote route and telemetry](https://github.com/open-telemetry/opentelemetry-demo/blob/3.1.0/src/quote/app/routes.php),
[C++ exporters](https://github.com/open-telemetry/opentelemetry-demo/blob/3.1.0/src/currency/src/meter_common.h).
