# Metrics Server

Metrics Server provides `metrics.k8s.io/v1beta1` for `kubectl top nodes`,
`kubectl top pods`, and CPU/memory resource metrics used by HPA/VPA integrations.
Running it alongside VictoriaMetrics is normal: Metrics Server supplies recent
resource usage to Kubernetes, while VictoriaMetrics stores monitoring history,
serves PromQL, and supports alerts and dashboards. KEDA's external-metrics adapter
serves a different API; installing KEDA does not supply `metrics.k8s.io`.

The official chart is pinned to `3.14.0` (application `0.9.0`), verified against
the upstream chart index on 2026-11-01. The shared HelmRelease is suspended until
a cluster overlay enables it. Requests are 100m CPU and 200Mi memory for one
replica. No persistent storage or dependency on the VictoriaMetrics stack is
required.

## Dependencies and TLS

The chart depends on monitoring CRDs and cert-manager. Its serving certificate
is issued through the chart's cert-manager integration; cainjector fills the
APIService's CA bundle and APIService TLS verification remains enabled.

The chart's ServiceMonitor defaults to skipping TLS verification. A Helm
post-render patch replaces that setting with the generated certificate's CA and
`metrics-server.observability.svc` server name. Apply the HelmRelease to retain
this patch. If renaming the release or namespace, update this reference and the
Secret reference alongside the chart settings.

Kubelet TLS verification is a **separate** connection. The shared template retains
verification and expects trusted kubelet serving certificates with appropriate
address SANs. The `iximiuz-platform` overlay explicitly adds
`--kubelet-insecure-tls` for the default kubeadm lab certificates and schedules
Metrics Server on a worker. Do not copy that exception into a cluster with
properly issued serving certificates. It does not disable TLS verification for
the aggregated Metrics API or the ServiceMonitor.

## Enable and verify

The full platform overlay includes a Kustomization depending on monitoring CRDs
and cert-manager, with health checks for both HelmRelease and APIService. For
another cluster, reconcile the `metrics-server` HelmRepository, create the target
namespace, and select this component with equivalent dependencies.

From the cluster's admin shell:

```sh
flux get kustomizations -A
kubectl -n observability get helmrelease metrics-server
kubectl -n observability get certificates.cert-manager.io metrics-server
kubectl wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io --timeout=3m
kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes
kubectl top nodes
kubectl top pods -A
```

Allow initial kubelet samples to arrive after startup. If the API is unavailable,
inspect APIService conditions, certificate readiness, network reachability, and
Metrics Server logs:

```sh
kubectl describe apiservice v1beta1.metrics.k8s.io
kubectl -n observability logs deployment/metrics-server --tail=100
```

Only one installation should own this cluster-wide APIService. The component has
been rendered locally with Helm 3 and 4; this template change does not claim live
Metrics API readiness or resume the paused control-plane diagnosis.

References: [Metrics Server](https://github.com/kubernetes-sigs/metrics-server),
[official Helm chart](https://kubernetes-sigs.github.io/metrics-server/).
