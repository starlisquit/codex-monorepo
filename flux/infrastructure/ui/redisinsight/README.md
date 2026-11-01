# Redis Insight

Select [this namespace base](../../namespaces/ui/kustomization.yaml) in foundation
or the deployment wrapper before this template. No all-namespaces bundle is
required; this directory does not create its own namespace.

Opt-in deployment of Redis Insight 3.8.0 using [Redis's official Kubernetes
manifests](https://redis.io/docs/latest/operate/redisinsight/install/install-on-k8s/).
**There is no official Redis Insight Helm chart.** Community charts exist but
are not substituted here. This is an explicit exception to the requested
Helm installation method, preserving official installation provenance.

The image is pinned by version and digest. Adaptations from the official
persistent-storage example: internal ClusterIP, Recreate strategy, default
StorageClass, fsGroup for the mounted data directory, explicit bind address,
disabled service environment links, health probes and bounded resources.
The service name avoids the environment variable collision documented by Redis.

Before applying, create `ui/redisinsight-encryption` with key `key` through your
secret manager. Generate a high-entropy key once and retain the same key with
the PVC across restarts/upgrades. This maps to the official `RI_ENCRYPTION_KEY`
setting. Never commit credentials. Preserve both the key and the 2Gi PVC to
recover saved connections. The key alone does not select encryption: enable
"Encrypt sensitive information" in the application's initial settings.

Include this directory in your chosen cluster's Flux Kustomization; it is not
enabled in the full-platform overlay. No HelmRepository or HelmRelease is
created because Redis does not provide a chart for this application.

Access using `kubectl -n ui port-forward svc/redisinsight-service 5540:5540`.
Complete the application's own setup, then add the Redis/Valkey endpoint,
authentication and TLS settings. Existing platform Valkey uses TLS; configure
its trusted CA and credentials. The validation fixture uses an isolated
password-protected Redis server and does not validate platform Valkey TLS.
Ingress is omitted; add access control before exposing this administrator UI.

See [browser verification](../../../docs/findings/redis-nui-ui-validation-2026-11-01.md)
for onboarding, connection and real browser read/write checks. The
[original API validation](../../../docs/findings/redis-nui-validation-2026-11-01.md)
records the earlier run and installation-method limitation.

## Optional OpenBao credentials (redisinsight)

Select [the credential opt-in](opt-in/external-secrets/README.md) to supply its
existing Secret references through External Secrets instead of manual provisioning.
