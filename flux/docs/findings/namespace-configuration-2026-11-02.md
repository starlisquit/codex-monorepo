# Namespace configuration: default and custom verification

**Passed on both fresh K3s playgrounds.** Scope: namespace configuration only,
on `feat/namespace-configuration`; main was not changed. Tested workload revision
`8e0f29bdbf31ed869890e7a5535a9c3f2a1a8c74`. Later changes document results and
improve validation diagnostics; they do not change the tested namespace manifests.

## Consumer result

Edit one generated cluster file, `flux-system/namespace-overrides.yaml`, instead
of maintaining namespace/DNS/SAN/role-binding patches in each application wrapper.
Omitted entries retain the existing defaults. The contract has 18 namespace groups;
only selected namespace/source bases are installed. `flux-system`/`kube-system`
remain fixed. See the [consumer guide](../operations/namespace-configuration.md).

Flux natively substitutes `${NS_*}` from the bootstrapped public ConfigMap.
The root resolves child health-check references, and every child uses the same
map for its own objects. Strict mode rejects missing values. Infrastructure
OpenBao credential opt-ins expose rendered role/policy descriptors so external
backend provisioning uses the same namespace bindings. KV paths, role names,
credentials, certificate ownership and issuer identities stay unchanged.

## Offline checks

- All **133 shared bases** rendered under default and independently renamed
  namespace profiles, with identity, namespace-reference, service DNS, certificate
  SAN and rendered role-namespace checks.
- **70 compositions / all 14 Components**, plus nine application credential
  opt-ins/ten Secret contracts, passed under **both** profiles.
- An independent comparison against main found identical default rendered
  objects across all 133 bases, excluding only the new non-secret role descriptor
  ConfigMaps and CRD substitution opt-out annotations.
- Unknown, empty, malformed, reserved and duplicate namespace mappings were
  rejected by the validation contract. Missing variables failed native strict
  Flux envsubst. Unescaped foreign interpolation and namespace fallback syntax
  were rejected by the namespace-only validation guard.
- All new run bootstrap/root/child substitution wiring and strict controller
  configuration passed validation. The full routine also checks retained run
  DAGs and standalone Kustomize builds.

Native application expressions needed explicit protection: `${DS_PROMETHEUS}` and
`${env:MY_POD_IP}` would otherwise be substituted. They are escaped as `$${...}`
in source and restored after one Flux pass. CRD schema descriptions contain
illustrative `${...}` expressions, so vendored CRDs explicitly opt out of
substitution without changing their schema definitions. `$()` remains untouched.

## Actual live verification

| Profile | Playground | Namespace placement |
| --- | --- | --- |
| Defaults | `6ae7b92c7f32053bde2df998` | ai, secrets, certificates, databases, observability, demo |
| Custom | `6ae7b92b7f32053bde2df984` | custom-ai, custom-secrets, custom-certificates, custom-databases, custom-observability, custom-demo |

Both were created in parallel and Flux followed each exact fresh run folder on
the feature branch. K3s `v1.37.1+k3s1`, Flux2.10.0, cert-manager1.21.3,
trust-manager0.26.0, OpenBao chart0.30.6/server2.7.2, ESO2.14.0,
CNPG operator0.29.1 and LiteLLM1.106.6 were deployed. Each run selected only
relevant prerequisites, a two-instance PostgreSQL cluster, actual LiteLLM,
a credential-checking OpenAI fixture and an agent-consuming application.

Both profiles passed:

1. OpenBao authentication roles were provisioned from the **rendered bootstrap
   ConfigMap**, and server-side role namespace bindings matched it. The actual
   service-account JWT authenticated; unrelated KV reads returned HTTP403.
2. ESO delivered master/salt/provider credentials with exact value matching;
   only hashes are retained in the evidence.
3. PostgreSQL completed verified TLS1.3 using the configured namespace-qualified
   Service DNS. Wrong CA and wrong hostname were rejected. Certificate SANs
   included that new DNS name; the operator ran in the separately configured
   database namespace. An independent psql connection used verify-full and
   reported SSL enabled.
4. Database-backed LiteLLM became ready, listed its model and completed an
   authenticated request through the real credential-checking fixture.
5. The real injector admitted an application in the configured demo namespace,
   authenticated against the moved OpenBao HTTPS endpoint, and rendered the file
   consumed by that application. The application's container did not mount the
   agent login token.
6. A separate Flux Kustomization deliberately omitted the namespace map. The
   actual strict controller returned BuildFailed for missing NS_AI, and its
   ConfigMap was never applied. The negative fixture Kustomization was deleted.
7. A Flux-applied ConfigMap preserved literal Grafana/OpenTelemetry `${...}` and
   Kubernetes `$()` expressions exactly.
8. Only the six selected namespace groups were created. In the custom run their
   old default namespaces were absent; unused groups such as proxy/quality were
   absent too. Merely defining the map did not deploy them.

At capture, all **16 Flux Kustomizations and seven HelmReleases per run** were
Ready at the tested revision. Evidence timestamps use UTC; local captures were
2026-11-02 **01:26:45 / 01:27:22 Europe/Istanbul** for default/custom respectively.

Evidence: [defaults](evidence/namespace-defaults-2026-11-02.json),
[custom](evidence/namespace-custom-2026-11-02.json). Scripts and selected settings
remain under the new run folders. No passwords, JWTs, administrator tokens,
recovery shares or private signing keys were exported to Git.

## Limits

This tests fresh placement, not migration of running stateful installations.
Groups move together, group consolidation is rejected, and bootstrap namespaces
stay fixed. OpenBao backend policies/roles still require authorized provisioning;
the descriptor is not an automatic administrator. Arbitrary Deployment primitive
role examples remain consumer-adapted examples. Raw Kustomize/Helm values now
require the documented Flux render step.

The live tests cover the selected PKI/OpenBao/ESO/CNPG/LiteLLM/injector stack,
not every infrastructure chart under a custom namespace. The full shared-template
matrix covers other templates offline. No new upstream model, HA, CA migration,
certificate-renewal/failover or browser suite is claimed. Root/key custody and
operator-owned credentials retain their existing ownership.

## Teardown

Publish results/configuration to both feature-branch remotes before destroying
these verified playgrounds. Record confirmed destruction afterwards. The PR is
opened only after checks and review are complete.
