# Application credential opt-ins: implementation and offline verification

Date: 2026-11-01. No playground was created for this change.

Nine opt-in Kustomizations provide ten Secret contracts for LiteLLM, SonarQube
(monitoring and a separate external-database mode), GitLab Runner, Renovate,
RedisInsight, NUI inline connection contexts, ClickHouse default-user credentials
and Velero S3 credentials. Each has its own namespace-local SecretStore and
service account, a short-lived Kubernetes authentication role bound to that
account/namespace/audience, and an exact-path read-only OpenBao KV policy.

Trust uses the public `platform-ca` ConfigMap. No PKI resources, operator-generated
credentials or chart-generated Secrets were changed. Application chart values
and existing credential references were preserved. Backend policy/role definitions
contain no secret values and require explicit authenticated provisioning; creating
Kubernetes objects does not configure the OpenBao backend or populate KV.

## Checks performed

The routine `validate.sh` passed:

- Seven retained run configurations and shared platform checks.
- 46 opt-in compositions covering all 12 existing Kustomize Components.
- Nine credential opt-ins and ten target Secret contracts, checked against actual
  application configuration, with namespace/role/SA/audience isolation,
  exact-path policies, public-CA trust, target keys and ownership uniqueness.
- Each credential opt-in composed with its owning application; all integrations
  composed together; LiteLLM and SonarQube monitoring integrations separately
  composed with their CNPG cluster and integration without claiming CNPG Secrets.
- 214 standalone Kustomize builds and `git diff --check`.

These are offline rendering/contract checks. No new live ESO authentication,
backend permission denial, refresh, application restart or upstream credential
rotation tests were performed. The previous OpenBao/ESO verification only proves
the underlying integration path, not live coverage of these new application paths.

## Operational boundaries

See [setup and coverage](../operations/application-external-secrets.md) and each
opt-in README for Secret names, properties, KV paths, backend setup, prerequisites
and Flux readiness ordering. Existing manually provisioned Secrets require an
explicit ownership handover. Environment-based credentials require Pod recreation
to consume updates. ESO refresh does not rotate upstream credentials. Encryption
keys require stable custody and coordinated data migration if changed.
