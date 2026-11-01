# OpenTelemetry Demo through native Victoria agents

The official demo chart remains pinned to `0.42.6` (application `3.1.0`, Collector
`0.160.0`). Its instrumented services and automatic five-user load generator stay
enabled. There is no telemetrygen deployment or separate JSON log generator.

## Telemetry paths

```text
Official demo SDKs (OTLP/gRPC and OTLP/HTTP)
  └─ demo Collector: protocol compatibility and existing demo scraping
       ├─ OTLP/HTTP metrics → VMAgent :8429 → VictoriaMetrics
       ├─ OTLP/HTTP logs    → VLAgent :9429 → VictoriaLogs
       └─ OTLP/HTTP traces  → VTAgent :10429 → VictoriaTraces
```

Every storage export goes through a native agent; the Collector has no direct
storage-backend exporter. It no longer exposes a Prometheus metrics endpoint or
runs span-to-metrics conversion. The span-derived dashboard has been removed.
SDK metrics remain enabled and are sent as cumulative OTLP metrics to VMAgent.
The Collector's own OTLP telemetry and its existing demo dependency scrapers use
that same metrics path.

## Why the Collector is retained

Some official demo images cannot switch protocols using environment variables.
For example, application `3.1.0`'s C++ currency service explicitly constructs gRPC
metric, log, and trace exporters. VMAgent's native OTLP ingestion is HTTP/protobuf,
and browser instrumentation uses another OTLP encoding. The existing Collector
provides the compatible receiving/conversion endpoint for those SDKs, without
requiring custom application images. Removing it entirely would need changes to
those applications or another protocol bridge.

The demo's built-in Prometheus, Grafana, Jaeger, and OpenSearch remain disabled.
Grafana and storage are supplied by the existing VM stack. SDK instrumentation
is still responsible for creating application telemetry; native agents forward
it rather than automatically instrumenting applications.

## Agent configuration

- VMAgent already receives HTTP/protobuf at `/opentelemetry/v1/metrics` on 8429
  and forwards to the stack's VMSingle.
- The VM stack enables VLAgent in **push mode**, with `k8sCollector.enabled: false`.
  It receives OTLP logs at `/insert/opentelemetry/v1/logs` on 9429 and forwards via
  the native protocol to VLSingle. No host log tailing or host filesystem mounts
  are required for this demo's SDK log path.
- The existing VictoriaTraces agent receives HTTP OTLP traces at
  `/insert/opentelemetry/v1/traces` on 10429 and forwards to VTSingle.

This collects the SDK logs exported by the demo. Container stdout/stderr is a
separate source and is not tailed by this push-mode VLAgent.

## Install and observe

1. Prepare Rook/Ceph, the `ceph-block` StorageClass, monitoring CRDs, Grafana
   Operator, and the VM stack. Its VLSingle/VTSingle retain seven days of data
   with a 10Gi volume each.
2. Enable the existing VictoriaTraces agent release. Confirm VMAgent, VLAgent,
   VTAgent, and their storage backends are running and healthy.
3. Reconcile the shared chart sources and this demo directory. It creates the
   `demo` namespace. Unsuspend the demo HelmRelease intentionally; it depends on
   the VM stack, monitoring CRDs, and VictoriaTraces agent release.

The full application remains substantial: 26 workload controllers and container
memory limits totaling 6,904Mi, plus native agents, backends, and other platform
services. Reserve adequate capacity before enabling it. All releases remain
suspended in Git; no cluster deployment is performed by adding these templates.

For storefront access after deployment:

```sh
kubectl -n demo port-forward service/frontend-proxy 8080:8080
```

Use the existing Grafana Explore datasources: **VictoriaMetrics** for application
and Collector metrics, **VictoriaLogs (DS)** for logs, and **VictoriaTraces** for
traces. Span-derived counters such as `traces_span_metrics_calls_total` are no
longer generated. Application metric names depend on their SDKs and VM's OTLP
conversion; discover actual series before building workload dashboards. Automatic
cross-signal links are not configured.

When enforcing network isolation, permit the Collector's egress to observability
TCP 8429/9429/10429, application OTLP traffic to the Collector, required demo
service/dependency traffic, and the agents' storage forwarding. No new ingress,
Gateway, or example policy is introduced. Update URLs for different namespaces,
release names, or cluster domains.

## Validation scope

Helm/Kustomize renders and the generated Collector configuration are checked.
Local smoke testing uses pinned native agents/backends and synthetic telemetry;
it does not establish that every official demo workload functions in a deployed
Kubernetes cluster. Live SDK export, agent queues, storage ingestion, and Grafana
queries still require cluster validation.

References:

- [Official demo chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-demo)
- [Pinned C++ metric exporter](https://github.com/open-telemetry/opentelemetry-demo/blob/3.1.0/src/currency/src/meter_common.h)
- [VMAgent OTLP ingestion](https://github.com/VictoriaMetrics/VictoriaMetrics/blob/v1.155.0/app/vmagent/main.go)
- [VLAgent](https://docs.victoriametrics.com/victorialogs/vlagent/)
- [VTAgent](https://docs.victoriametrics.com/victoriatraces/vtagent/)
