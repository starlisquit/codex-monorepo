# ServiceMonitor opt-in

Select this Kustomize Component with the Deployment base. It adds:

- `monitoring.coreos.com/v1` ServiceMonitor `application`.
- Internal ClusterIP Service `application-metrics`, with named port `metrics`
  (8081) targeting the Pod's named `metrics` port.
- Container port `metrics` (8081) on container `application`.

The monitor selects the dedicated metrics Service by application and metrics
component labels, in its own namespace. That Service selects the application
Pods. The endpoint requests `/metrics` every 30s with a 10s timeout. The separate
`opt-in/service` HTTP Service is optional; this component works without it and
can be combined with it without creating duplicate Services.

The application must actually serve Prometheus metrics. The HTTP echo starter
does not expose them; replace its image/command and configure the endpoint for
your app. Port declarations and monitor objects do not add instrumentation.

Example wrapper at `flux/clusters/<run>/my-app/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: api-
resources:
- ../../../infrastructure/primitives/deployment
components:
- ../../../infrastructure/primitives/deployment/opt-in/servicemonitor
# Add opt-in/service separately if this app also needs its HTTP Service.
labels:
- pairs:
    app.kubernetes.io/name: api
  includeSelectors: true
  includeTemplates: true
```

The supplied selector configuration keeps monitor, Service and Pod labels aligned
under consumer label transformations. Use a unique selector per workload.
Install the [monitoring CRDs](../../../../observability/prometheus-operator-crds)
and wait for ServiceMonitor to be Established before reconciling this component.
A compatible collector must select the monitor and have permission/network
access. The repository enables VictoriaMetrics' Prometheus resource conversion
and VMAgent selection of converted scrape resources; CRDs alone do not scrape.

Patch `endpoints` for path/interval/TLS/authentication. Store credentials in
referenced Secrets. When changing the application's numeric metrics port,
change the Deployment port named `metrics`; Service `targetPort: metrics` and
monitor `port: metrics` continue resolving by name. Change the Service's numeric
port too if clients must use the new number. Normally choose either this component
or PodMonitor for the same target to avoid duplicate scraping.

Build/selector/schema checks passed; runtime scraping has also been verified in a focused cluster. Verify collector discovery, target health and an
actual app metric after deployment.

[Focused runtime scraping verification](../../../../../docs/findings/monitor-components-runtime-2026-11-01.md)
passed through VictoriaMetrics conversion and VMAgent, including namespace
isolation, a broken selector and recovery after Pod replacement. Routine
`validate.sh` now exercises all Component combinations and selector contracts.
