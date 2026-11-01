# NUI (NATS UI)

Opt-in template using the [official NUI chart](https://github.com/nats-nui/k8s),
version 0.1.6. Upstream labels Kubernetes support experimental.
The application version is explicitly pinned rather than using the chart's `latest` default.

Build with `kubectl kustomize flux/infrastructure/broker/nui` and include the
resulting resources in your chosen cluster's Flux Kustomization. Ensure the
shared Helm sources and a default StorageClass are available. This template
is not enabled in the full-platform overlay.

A single StatefulSet stores saved connections and schemas on its 1Gi RWO PVC.
The schema paths are redirected under `/db` because the image's default schema
directories are not writable by the application user. Deleting a release does
not automatically remove its StatefulSet PVC.

Create Secret `broker/nui-contexts` outside Git with key `platform.json`
containing a [NATS CLI context](https://github.com/nats-nui/k8s#cli-context-secrets).
Set its URL to your actual NATS service and configure authentication and TLS
with the broker's real credentials and CA. The existing NATS template requires
TLS; a plaintext test URL is only suitable for the isolated validation fixture.
For credentials files, configure `credsVolume.items` and supply `nui-creds`.
The chart treats context/credential Secrets as optional, so Pod readiness alone
does not prove that a broker connection works.

Access privately with `kubectl -n broker port-forward svc/nui 31311:31311`.
Ingress is disabled. NUI exposes saved connections and broker operations to
its users; put an authentication gateway in front before exposing it beyond
trusted administrators. Namespace and ClusterIP alone are not authorization.

Validation results and known upstream issues are recorded in
[the findings report](../../../docs/findings/redis-nui-validation-2026-11-01.md).
