# NUI (NATS UI)

Namespaces are defined centrally in [the namespace bundle](../../namespaces/README.md).
Reconcile that foundation before this template; this directory does not create
its own namespace.

Opt-in template using the [official NUI chart](https://github.com/nats-nui/k8s),
version 0.1.6. Upstream labels Kubernetes support experimental.
The application image is pinned by version and multi-architecture digest rather
than using the chart's `latest` default.

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

## Browser compatibility fixes

The official 0.10.0 image has two browser defects: absent session storage is
parsed as null, and an empty bucket-list response is treated as an array.
`start.sh`, supplied by ConfigMap `nui-startup`, corrects those defaults in the
served JavaScript before invoking the official entrypoint. It also redirects
schema directories to the existing writable `/db` volume. This is a local
compatibility patch to the official image, not an upstream release fix.

Every browser receives the corrected code. Tests do not seed localStorage or
intercept application API responses. Existing valid sessions are preserved;
missing/null layout uses the upstream default right-hand drawer, and missing
collections use empty arrays. The first KV bucket can be created from an empty
broker without a page error.

The patch checks for known bundle fragments and fails startup if they cannot
be found. Review it when upgrading the image; do not remove the image digest
or bypass the guard. Bump `podAnnotations.infrastructure.codex/nui-compatibility-patch`
when changing `start.sh` so Helm rolls the StatefulSet. The script requires the
image's writable frontend directory and current entrypoint privilege model.

See [browser verification](../../../docs/findings/redis-nui-ui-validation-2026-11-01.md)
for the corrected UI results. The [original findings](../../../docs/findings/redis-nui-validation-2026-11-01.md)
retain the failures observed before these fixes.
