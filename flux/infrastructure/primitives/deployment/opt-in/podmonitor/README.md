# PodMonitor opt-in

Select this Kustomize Component with the Deployment base to discover Pods
directly, without any Service. It adds `monitoring.coreos.com/v1` PodMonitor
`application` and a container port named `metrics` (8081) to container
`application`. The monitor requests `/metrics` every 30s, with a 10s timeout.
It selects only matching Pods in its own namespace.

The application must actually serve Prometheus metrics on that port. Declaring
a container port does not start a listener or instrument the application; the
HTTP echo starter does not expose Prometheus metrics. Patch the image/command
and endpoint configuration for the real workload. HTTP probes remain on `http`.

Example wrapper at `flux/clusters/<run>/my-app/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: api-
resources:
- ../../../infrastructure/primitives/deployment
components:
- ../../../infrastructure/primitives/deployment/opt-in/podmonitor
labels:
- pairs:
    app.kubernetes.io/name: api
  includeSelectors: true
  includeTemplates: true
```

The Deployment's Kustomize configuration transforms monitor selectors along with
Pod labels. Use a unique selector per workload, as described in the Deployment
README. Configure additional monitor metadata labels to match your collector's
selection policy, if required.

Install the [monitoring CRDs](../../../../observability/prometheus-operator-crds)
and wait for PodMonitor to be Established before reconciling this component.
A compatible collector must select the monitor and have permission/network
access to the Pods. The repository's VictoriaMetrics operator enables Prometheus
resource conversion; its VMAgent selects all converted scrape resources by
default. The CRD-only release does not install a collector.

Patch `podMetricsEndpoints` for a different named port, path, interval, TLS or
authentication. Keep credentials in referenced Secrets. If only the numeric
metrics port changes, patch the container port named `metrics`; discovery still
uses the port name. Normally select either PodMonitor or ServiceMonitor for the
same target, since enabling both can duplicate scrapes.

Build/selector/schema checks passed. End-to-end scraping of these new opt-ins
has not been runtime-tested. After deployment, verify collector discovery, target
health and an actual application metric; monitor existence alone is insufficient.
