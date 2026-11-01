# Platform documentation

Read these documents for design decisions, observed behavior, and limitations.
Use [runbooks](../runbooks/README.md) when you need executable procedures.

- [Architecture and deployment dependencies](architecture/deployment-order.md)
- [Playground sizing and the control plane](architecture/playground-sizing.md)
- [Fresh rebuild verification](findings/rebuild-verification.md)
- [Historical deployment findings](findings/deployment-findings.md)
- [Cilium kube-proxy migration record](findings/kube-proxy-migration.md)
- [Resource pressure and the reduced demo](findings/resource-pressure.md)
- [Storage and Ceph CSI findings](findings/storage.md)
- [Flux, Helm, UI, and Collector findings](findings/flux-and-helm.md)
- [Monitoring, certificates, and telemetry findings](findings/observability.md)
- [Secrets and persistence responsibilities](operations/secrets-and-data.md)

The findings are dated observations, not a live status dashboard. The fresh
rebuild record distinguishes current verification from incidents on the destroyed
play. Render validation, controller readiness, and end-to-end application
verification are different levels of evidence.

- [Recurring log errors and their relevance](findings/log-error-review.md)
