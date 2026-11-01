# Infrastructure web UIs

## Headlamp

`headlamp/` deploys the Kubernetes web UI using the official Headlamp Helm chart,
pinned to stable version `0.46.0` (verified on 2026-11-01).

Create the `ui` namespace, reconcile the shared chart sources, then add a Flux
Kustomization targeting `./flux/infrastructure/ui/headlamp`. Remove the release's
suspension when ready to install. Validate with:

```sh
kustomize build flux/infrastructure/ui/headlamp
```

The service is ClusterIP, with ingress and HTTPRoute disabled. After deployment,
use local port forwarding for access:

```sh
kubectl -n ui port-forward service/headlamp 8080:80
```

Sign in with an appropriately scoped Kubernetes bearer token. The application
service account is not granted cluster-admin, and Headlamp's unsafe shared
service-account authentication is disabled. Users' own Kubernetes RBAC permissions
control their access. Configure OIDC or authenticated ingress separately if needed;
keep credentials in Secrets rather than chart values committed to Git.

## NATS

The existing NATS chart `2.15.2` does not bundle a web management UI. It includes
NATS HTTP monitoring endpoints, an optional Prometheus exporter, and the `nats-box`
CLI toolbox. Monitoring endpoints are not a graphical administration console.
A NATS web management UI would require a separate deployment; none is added here.

References:

- [Headlamp chart](https://github.com/kubernetes-sigs/headlamp/tree/main/charts/headlamp)
- [NATS chart](https://github.com/nats-io/k8s/tree/main/helm/charts/nats)
- [NATS monitoring](https://docs.nats.io/running-a-nats-service/nats_admin/monitoring)

## Flux Web UI

[`flux-ui/`](flux-ui) uses the official chart's standalone web-server mode.
It does not install or manage Flux controllers, FluxInstances, or operator CRDs.
Bootstrap Flux separately, then reconcile this suspended UI release. See its
README for local access and monitoring settings.
