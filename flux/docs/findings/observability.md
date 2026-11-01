# Observability findings

The platform uses the VictoriaMetrics operator's Prometheus resource converter.
ServiceMonitors and PodMonitors become VM scrape resources; VMAgent selects them
across namespaces. Grafana Operator imports dashboards and datasources into the
bundled Grafana through an external binding and generated Secret references.
The Grafana sidecars remain disabled to avoid competing provisioning owners.

Observed: 55 dashboard resources and five datasource resources synchronized,
and 71 of 74 scrape series had `up=1` at a recorded check. This count changes as
components and targets appear and must not be used as a permanent success value.

## Control-plane metrics are unfinished

kube-controller-manager and kube-scheduler originally bound to localhost. Their
bind addresses were changed to allow internal access, but TLS verification still
failed: the serving certificates covered localhost/127.0.0.1, not the target name
or IP used by the chart. Etcd scraping also failed with an unknown CA.

An attempt to extend etcd's metrics listener interrupted the API and was reverted.
Etcd retains its original localhost metrics listener. Do not copy that attempted
change into a bootstrap recipe, reuse etcd administrative client keys for routine
scraping, or describe those three targets as healthy.

A future fix should establish suitable serving certificates/trust and the intended
metrics endpoint, then validate the exact scrape path. This change set does not
disable TLS verification to make the targets look healthy. API slowness diagnosis
was separately paused by the user.

## Telemetry signals are separate checks

The demo's Collector receives OTLP/gRPC and OTLP/HTTP, then forwards through:

| Signal | Native agent | Ingest path | Storage |
| --- | --- | --- | --- |
| Metrics | VMAgent `:8429` | `/opentelemetry/v1/metrics` | VMSingle |
| SDK logs | VLAgent `:9429` | `/insert/opentelemetry/v1/logs` | VLSingle |
| Traces | VTAgent `:10429` | `/insert/opentelemetry/v1/traces` | VTSingle |

VLAgent is push-only here; it does not tail container stdout/stderr. There is no
span-to-metrics pipeline. Native agents do not automatically instrument services.
Backend readiness and `up` series do not prove demo SDK logs or traces arrived.
Use the [verification runbook](../runbooks/operations/verify-platform.md),
Collector queue/error counters, real backend queries, and Grafana Explore.

Kubernetes can expose similarly named resources from multiple API groups. Use
`grafanas.grafana.integreatly.org` explicitly when checking the operator binding;
the unqualified `kubectl get grafana` returned no resources during this deployment
even though the intended binding existed and was synchronized.
