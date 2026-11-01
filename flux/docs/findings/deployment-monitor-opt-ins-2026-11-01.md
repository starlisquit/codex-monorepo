# Deployment monitoring opt-ins — 2026-11-01

Added workload-specific monitoring resources under
`infrastructure/primitives/deployment/opt-in`, alongside the Deployment they
select. Monitoring CRDs, operators and collectors remain in observability.

- `podmonitor`: PodMonitor plus a named metrics container port; discovers Pods
  directly without a Service.
- `servicemonitor`: ServiceMonitor, dedicated `application-metrics` ClusterIP
  Service, and named metrics container port. Independent of the HTTP Service
  opt-in, and can be combined with it without duplicate resources.
- Both use `monitoring.coreos.com/v1`, port name `metrics` (8081), `/metrics`,
  interval 30s and timeout 10s. Namespace selectors are omitted, so target
  discovery stays in the monitor's own namespace.
- A Kustomize transformer configuration maps consumer label changes into monitor
  selectors, keeping application/Service/Pod targeting consistent with prefixes
  and unique application selectors.

The application must expose Prometheus metrics; declaring a port and monitor
cannot instrument the HTTP echo starter. Select one monitor type per target
unless duplicate scraping is intentional. Monitoring CRDs must be Established,
and a compatible collector must select the resource and have target access.
The existing VictoriaMetrics configuration enables Prometheus resource conversion
and selection of converted scrape resources; the CRD-only chart is not a collector.

Validation passed:

- 163 repository Kustomize builds and all four retained run dependency checks.
- Official monitoring CRD schemas from pinned prometheus-operator-crds chart
  32.0.2, application v0.94.2.
- Five two-application compositions: PodMonitor; ServiceMonitor; HTTP Service +
  PodMonitor; HTTP Service + ServiceMonitor; both monitors together. Verified
  namespace/label transformations, one metrics port per container, preserved HTTP
  port/probes, Pod selection isolation and exact dedicated Service selection.
- An unselected Deployment renders identically to the previous committed base.

No playground was created. End-to-end target discovery, scraping and stored
application metrics for these new opt-ins have not been runtime-tested.
