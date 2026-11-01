# Platform documentation

Read these documents for design decisions, observed behavior, and limitations.
Use [runbooks](../runbooks/README.md) when you need executable procedures.

- [CI and quality chart verification](findings/ci-quality-validation-2026-11-01.md)
- [Tetragon, Trivy and security dashboard verification](findings/security-validation-2026-11-01.md)
- [NGINX and LiteLLM deployment verification](findings/proxy-ai-validation-2026-11-01.md)
- [Interrupted full-platform verification](findings/validation-2026-11-01.md)

- [Next iximiuz Labs validation checklist](../runbooks/operations/next-lab-validation.md)
- [Last run: teardown and unfinished PKI migration](findings/pki-last-run.md)
- [Current template PKI coverage](architecture/pki-coverage.md)
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
