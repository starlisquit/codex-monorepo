# Application credentials through OpenBao

Application credential integrations are opt-in resources beneath each template's
`opt-in/external-secrets/`. SonarQube additionally has
`opt-in/external-database-secrets/` for its base external-database mode. Existing
application defaults and manually provisioned Secrets remain supported.

## Coverage

| Template | Opt-in | Target Secrets |
|---|---|---|
| LiteLLM | [external-secrets](../../infrastructure/ai/litellm/opt-in/external-secrets/README.md) | `litellm-auth`, `litellm-provider-credentials` |
| SonarQube | [external-secrets](../../infrastructure/quality/sonarqube/opt-in/external-secrets/README.md) | `sonarqube-monitoring` |
| SonarQube external database only | [external-database-secrets](../../infrastructure/quality/sonarqube/opt-in/external-database-secrets/README.md) | `sonarqube-database` |
| GitLab Runner | [external-secrets](../../infrastructure/ci/gitlab-runner/opt-in/external-secrets/README.md) | `gitlab-runner-auth` |
| Renovate | [external-secrets](../../infrastructure/ci/renovate/opt-in/external-secrets/README.md) | `renovate-credentials` |
| RedisInsight | [external-secrets](../../infrastructure/ui/redisinsight/opt-in/external-secrets/README.md) | `redisinsight-encryption` |
| NUI | [external-secrets](../../infrastructure/ui/nui/opt-in/external-secrets/README.md) | `nui-contexts` |
| ClickHouse cluster | [external-secrets](../../infrastructure/databases/clickhouse/cluster/opt-in/external-secrets/README.md) | `clickhouse-auth` |
| Velero S3 | [external-secrets](../../infrastructure/backup/velero/opt-in/external-secrets/README.md) | `velero-cloud-credentials` |

## Ownership and prerequisite order

1. Install namespaces, cert-manager, the central issuer and trust-manager.
2. Issue OpenBao TLS, start OpenBao, initialize/unseal it, enable KV v2 at `kv`
   and Kubernetes authentication at `kubernetes` using the existing bootstrap
   runbook. Retain recovery material independently. No opt-in bootstraps OpenBao
   from secrets stored inside OpenBao.
3. Install External Secrets. Ensure `ConfigMap/platform-ca` is distributed into
   each consuming namespace by the existing trust Bundle. Stores verify OpenBao
   TLS using only that public CA; they never mount OpenBao's private TLS key.
4. Apply the selected credential opt-ins to create their rendered, non-secret
   `<store>-bootstrap` ConfigMaps, service accounts, stores and ExternalSecrets.
   Provision the descriptor's policy/role through an authenticated,
   TLS-verified OpenBao administration session, then securely populate its listed
   KV keys. The policy grants read access to exact application paths and lookup/renew/revoke
   operations on the caller's own token. ESO needs self-lookup to validate the
   provider when the OpenBao default policy is disabled. The
   role binds one application service account in one namespace with the `openbao`
   audience and short-lived tokens. No root token is delivered to ESO.
5. Apply the selected credential directories in a separate cluster-owned Flux
   Kustomization after External Secrets and OpenBao are ready. Set `wait: true`
   and a suitable timeout. Require every SecretStore and ExternalSecret to be
   `Ready=True`; the application Flux Kustomization should `dependsOn` that
   credentials stage. Keep the two stages separate to avoid starting Helm installs
   before required Secrets exist. Template selection alone does not add this
   cluster-owned wiring.

Example cluster credentials wrapper (relative path depends on its location):

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- ../../../infrastructure/ai/litellm/opt-in/external-secrets
- ../../../infrastructure/ci/renovate/opt-in/external-secrets
```

Each directory has unique application-specific service account and SecretStore
names, so multiple integrations in one namespace compose without duplicate
objects. The store is namespaced rather than an unrestricted ClusterSecretStore.
OpenBao RBAC/token-review configuration from the existing OpenBao chart and the
ESO controller's TokenRequest permissions are prerequisites. Cluster owners must
restrict who can create ExternalSecrets and request/use these service-account
tokens; policy isolation does not protect against namespace administrators.

## Data contract and ownership transfer

Default KV paths are `infrastructure/<namespace>/<application>/<purpose>`, relative
to the `kv` mount. Each opt-in documents exact Secret names, keys and provider
properties. These are reusable conventions, not credential values. For several
clusters sharing one OpenBao, use separate mounts or environment-prefixed paths
and update policies, roles and ExternalSecret references together. Never grant
multiple environments access merely by reusing default role names.

Secrets are ordinary Kubernetes Secrets at runtime. Configure Kubernetes encryption
at rest and appropriate RBAC independently. There are no plaintext credential
values, SOPS files or backend credentials in these integrations.

ESO uses `creationPolicy: Owner`: it is the sole reconciler of its target Secrets.
Do not point an integration at cert-manager, CNPG, Helm-generated or any other
controller-owned Secret. For existing manually created Secrets, review contents
and ownerReferences and perform an explicit ownership handover before enabling
ESO; do not delete working credentials as a generic migration step. Removing an
ExternalSecret can garbage-collect its owned Secret. `deletionPolicy: Retain`
means a missing **provider value** does not automatically delete the Kubernetes
Secret; it does not prevent Kubernetes owner-reference garbage collection.

The SonarQube main integration only manages its monitoring passcode; its separate
external-database integration is incompatible with the CNPG integration. LiteLLM's
CNPG credentials (`litellm-db-app`) and SonarQube's CNPG application credentials
remain generated and rotated by CNPG. Grafana's chart-generated credentials,
cert-manager TLS keys, trust bundles, OpenBao recovery material and controller
bootstrap credentials remain untouched. Templates without an existing external
credential contract are not modified to invent one.

## Refresh, rotation and failure behavior

ESO refreshes once per minute. It copies existing provider values; it does not mint
GitLab tokens, change actual database passwords or rotate provider API keys.
Coordinate upstream credential changes, KV updates and application reloads.
Environment variables require new Pods. Mounted Secret updates require application
reload support; subPath mounts do not receive updates. CronJobs use current values
only in newly created Pods. These opt-ins deliberately do not introduce a global
restart controller or claim automatic application reload.

Keep LiteLLM salt/master keys and RedisInsight encryption keys stable where stored
data depends on them; changing an encryption key is a data migration, not routine
password rotation. Back up OpenBao data and recovery material independently.
During an OpenBao outage already-synced Secrets remain available, but provisioning
and refresh fail; alert on SecretStore/ExternalSecret readiness and refresh age.

## Validation scope

`validate.sh` builds every credential directory, composes each with its owning
application and composes all of them together. Its credential checks enforce
unique ownership, exact KV policies, namespace/role/service-account/audience
bindings, public-CA-only trust and expected application Secret names/keys. These
routine checks are offline. Dedicated parallel K3s runs additionally verified all
nine infrastructure opt-ins (ten Secret contracts) through actual applications:

- [LiteLLM and SonarQube](../findings/infra-eso-apps-2026-11-01.md): proxy
  authentication/provider routing, monitoring passcode and external PostgreSQL password.
- [RedisInsight and NUI](../findings/infra-eso-ui-2026-11-01.md): encrypted
  saved Redis connection and authenticated NATS context, both after Pod replacement.
- [Runner and Renovate](../findings/infra-eso-ci-2026-11-01.md): real GitLab job
  execution and authenticated dry-run repository processing.
- [ClickHouse and Velero](../findings/infra-eso-data-2026-11-01.md): password-
  authenticated SQL and ConfigMap backup/restore against a local authenticated S3 fixture.

The live tests found and corrected missing self-token permissions in the original
policies. See each report for versions, lab overrides and limits; these runs do
not establish production HA, all-feature coverage or upstream credential rotation.

## Custom applications using the Deployment primitive

Select the primitive's [External Secrets Component](../../infrastructure/primitives/deployment/opt-in/external-secrets/README.md)
for environment-based credentials, or its [OpenBao injector Component](../../infrastructure/primitives/deployment/opt-in/openbao-injector/README.md)
for agent-rendered files. Both include scoped backend examples and preserve
application identity isolation when composed with name prefixes. They require
explicit backend provisioning and application-specific KV path configuration.

## Namespace configuration

The namespace-only Flux mapping also renders backend role bindings into each
opt-in's public bootstrap ConfigMap. Provision OpenBao from that rendered data,
not raw role.json files. See [the namespace consumer guide](namespace-configuration.md).
