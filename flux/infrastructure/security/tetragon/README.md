# Tetragon

A DaemonSet agent and stdout exporter on every node, plus the Tetragon operator.
Requires Linux/eBPF support and suitable kernel BTF. Cilium's CNI and Tetragon are
separate components; Tetragon does not replace the CNI. Existing kernel 6.1 is a
candidate, but BTF, kernel features and startup must be checked on the next play.

The chart retains its required capabilities/host mounts rather than forcing an
unsupported restricted-Pod profile. Its namespace permits privileged workloads;
chart 1.8.0 currently renders capability-based agent security rather than a
blanket privileged container. Limit permissions to create Pods in this namespace.
The gRPC control interface stays on the local Unix socket; no remote plaintext
control listener or new certificate is configured. Prometheus scraping is HTTP,
consistent with the current internal monitoring design.

## Event export

- Upstream process-cache sizes, default event kinds and export scope.
- No template-specific export rate cap or demo/application namespace restriction.
- Upstream noise filtering still excludes health checks and the configured default
  host/system namespaces; review those defaults for your visibility requirements.
- Process/parent argument fields are omitted from file-export events to reduce
  accidental credential capture. This is not a universal secret-redaction guarantee.
- Upstream rotating-file defaults and a stdout exporter integrate with vlagent.

Export filters affect event output, not which workloads the kernel probes observe.
They do not authorize access to the Unix socket or redact other outputs. Tetragon
normally needs broad Pod metadata visibility. Do not add arbitrary probes capturing
payloads or enforcement actions without reviewing their data and operational impact.

The chart installs its three CRDs through Helm (`crds.installMethod: helm`) and
its operator is told to skip CRD creation. The parent Flux resource waits for
TracingPolicy, namespaced TracingPolicy and PodInfo CRDs after the HelmRelease.
Review CRD/data retention before uninstalling; chart/Helm CRD lifecycle differs
between templated and `crds/` resources.

## Inspect

```sh
kubectl -n tetragon get daemonset,deployment,pods
kubectl get crd tracingpolicies.cilium.io tracingpoliciesnamespaced.cilium.io podinfo.cilium.io
kubectl -n tetragon logs daemonset/tetragon -c tetragon --tail=50
kubectl -n tetragon logs daemonset/tetragon -c export-stdout --tail=10
kubectl get tracingpolicies,tracingpoliciesnamespaced -A
```

An empty tracing-policy listing is expected here: built-in execution/exit events
are the initial feed. Generate a harmless exec in an approved demo Pod, inspect
an exported event with matching binary/Pod identity, and verify it reaches
VictoriaLogs. In the generic container-log dashboard select namespace `tetragon`
and container `export-stdout`: those outer Kubernetes labels identify the agent,
while nested event fields identify the observed application Pod. Events may have
Unknown log level, which does not mean they are low-risk or failed detections.
