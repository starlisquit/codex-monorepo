# NGINX Ingress Controller

Namespaces are defined centrally in [the namespace bundle](../../namespaces/README.md).
Reconcile that foundation before this template; this directory does not create
its own namespace.

Official [NGINX chart](https://github.com/nginx/kubernetes-ingress/tree/v5.7.0/charts/nginx-ingress),
`nginx-ingress` chart `2.8.0` / controller `5.7.0`, from `https://helm.nginx.com/stable`.
This is NGINX's open-source Ingress Controller, not the separate ingress-nginx
project or an NGINX Plus deployment. No Plus license is required.

The component creates namespace `proxy` and class `nginx`, without making it the
default class. Set `spec.ingressClassName: nginx` on intended application Ingresses.
Use the `nginx.org/*` annotation family supported by this controller; annotations
from another controller are not interchangeable. Custom VirtualServer resources
are disabled in this template; ordinary Kubernetes Ingress routes remain enabled.

The default Service is NodePort with Cluster traffic policy, requiring no cloud
load balancer. Discover allocated ports from the Service; do not assume fixed port
numbers. For a production load balancer, override `controller.service.type` and its
provider-specific settings. Metrics have an internal Service; ServiceMonitor creation
is off until the consuming cluster supplies monitoring CRDs.

Proxy buffering is disabled and the read timeout is 300 seconds to support streaming
API responses such as LiteLLM. TLS termination requires a same-namespace Secret in
the application Ingress namespace. No private keys or default certificate are
committed; configure DNS, issuer/renewal and public exposure in the consuming overlay.

```sh
kustomize build flux/infrastructure/proxy/nginx
helm repo add nginx-stable https://helm.nginx.com/stable
helm pull nginx-stable/nginx-ingress --version 2.8.0 --untar --untardir /tmp/nginx-chart
helm lint /tmp/nginx-chart/nginx-ingress -f flux/infrastructure/proxy/nginx/values.yaml
helm upgrade --install nginx nginx-stable/nginx-ingress --version 2.8.0 \
  --namespace proxy --create-namespace -f flux/infrastructure/proxy/nginx/values.yaml \
  --wait --timeout 10m
kubectl -n proxy get deployment,pods,service
```

For Flux, select the source and component in a dedicated consuming overlay, with
a HelmRelease health check. Do not use Helm CLI and Flux to manage the same release
concurrently. This optional template is not added to the full-platform overlay.
Verify an actual class-selected route and hostname/TLS behavior, not just Pod readiness.
