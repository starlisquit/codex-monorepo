# Deployment credential Components: offline verification

Added two Components under the existing singular
`infrastructure/primitives/deployment/opt-in/` directory:

- `external-secrets`: application-local login service account, TLS-verified
  namespaced OpenBao SecretStore, ExternalSecret and application `envFrom`.
- `openbao-injector`: workload service account, injector annotations, short-lived
  projected audience-bound token, and init/continuing agent JSON file delivery.

Both include scoped OpenBao policy and example role files. Backend configuration
and actual KV values require a separate authenticated administrative workflow.
Custom Kustomize references transform ESO targets/consumers/store/login identities
and injector role annotations with application name prefixes. Provider paths and
backend namespace bindings remain explicit consumer configuration. Separate paths
and identities permit environment-based and file-based delivery in the same Pod.

The injector annotations and named projected-volume behavior were checked against
`hashicorp/vault-k8s` v1.7.6 source, matching the injector used by the existing
OpenBao chart. The application does not mount its projected login token. Agent
UID/GID match the primitive; JSON output is 0400. TLS verification relies on the
public CA bytes already supplied to the shared injector. No CA/private-key,
operator credential or existing application-secret ownership was changed.

## Validation

Routine validation passed seven retained run configurations, 70 compositions
covering all 14 Components, nine existing application credential opt-ins/ten
Secret contracts, and 214 standalone Kustomize builds. Dedicated credential
assertions cover two composed applications, namespace/reference isolation,
application-specific provider paths, ESO target consumption, role/SA transforms,
agent identity, token audience/expiry/mount isolation and scoped backend examples.
All combinations with Deployment Service and monitor Components were rendered.

No playground was created and no live authentication, admission mutation, agent
rendering or application secret consumption was tested for these new Components.
The echo starter does not read the injected JSON or demonstrate credential use.
Backend examples must be adapted/provisioned before a live deployment.

## Operational requirements

The Component READMEs document ESO/OpenBao readiness, public trust prerequisites,
policy/role provisioning, path customization and refresh/reload behavior. The
injector's webhook failure policy is configured centrally, not by a workload
annotation; consumers requiring fail-closed admission must configure it and make
the application reject a missing credential file. Environment updates require new
Pods, while file updates require application reload. Token renewal permissions
apply only to the caller's own token; no default or broad KV policy is granted.

## Runtime follow-up

The initial offline-only scope above was subsequently extended with parallel
fresh K3s runs. See the [External Secrets runtime report](deployment-external-secrets-runtime-2026-11-01.md)
and [injector runtime report](deployment-injector-runtime-2026-11-01.md) for actual
credential delivery, isolation, refresh and failure results.
