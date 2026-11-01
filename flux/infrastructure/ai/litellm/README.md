# LiteLLM

Select [this namespace base](../../namespaces/ai/kustomization.yaml) in foundation
or the deployment wrapper before this template. No all-namespaces bundle is
required; this directory does not create its own namespace.

Official [BerriAI chart](https://docs.litellm.ai/docs/proxy/deploy),
`oci://ghcr.io/berriai/litellm-helm`, chart/application `1.106.6`.
The pinned chart reference is in `sources/litellm`. In namespace `ai`, this
component deploys a ConfigMap-backed model configuration and a ClusterIP Service.

The initial route is `gpt-4o-mini` through OpenAI. Adapt the model list for your
provider. Provision these same-namespace Secrets outside Git before deployment:

- `litellm-auth`, key `master-key`: a strong `sk-` prefixed proxy master key.
- `litellm-provider-credentials`, key `OPENAI_API_KEY`: your actual upstream key.

For preexisting secure files:

```sh
kubectl create namespace ai --dry-run=client -o yaml | kubectl apply -f -
kubectl -n ai create secret generic litellm-auth --from-file=master-key=/secure/litellm-master-key
kubectl -n ai create secret generic litellm-provider-credentials --from-file=OPENAI_API_KEY=/secure/openai-api-key
```

No token is embedded in Helm values or the model ConfigMap. The chart loads the
master key through its Secret reference and provider credentials as environment
variables. One worker runs by default with a 2 GiB memory limit. The ServiceAccount
does not mount Kubernetes API credentials. Ingress is off until a consuming overlay
provides a hostname and TLS Secret; see the lab override for an NGINX-class example.

The default is a database-free authenticated proxy. PostgreSQL, Redis and migration
Jobs are disabled together. This supports static model routing/master-key auth,
not a verified persistent virtual-key, budget, spend-history or admin-UI deployment.
In this database-free mode, missing API keys returned 401 and an invalid key
returned 400 with an error (the database-backed virtual-key fallback is unavailable).
Neither response exposed the model list or reached the upstream fixture.
To enable database-backed features, configure an external dedicated PostgreSQL
database and credential Secret, persistent encryption/salt key custody, and schema
migrations. An excluded example is provided at `opt-in/postgresql/values.example.yaml`; its connection and recovery behavior
must be verified in the consuming environment. No database credentials belong in Git.

```sh
kustomize build flux/infrastructure/ai/litellm
helm pull oci://ghcr.io/berriai/litellm-helm --version 1.106.6 \
  --untar --untardir /tmp/litellm-chart
helm lint /tmp/litellm-chart/litellm-helm -f flux/infrastructure/ai/litellm/values.yaml
helm upgrade --install litellm oci://ghcr.io/berriai/litellm-helm --version 1.106.6 \
  --namespace ai -f flux/infrastructure/ai/litellm/values.yaml --wait --timeout 15m
kubectl -n ai get deployments,pods,service
kubectl -n ai port-forward service/litellm 4000:4000
```

For Flux, select its OCI source/component in a dedicated consuming overlay after
credential provisioning; use a HelmRelease health check. It is not added to the
full-platform overlay. Do not manage the same release with Helm CLI concurrently.
Verify authenticated model discovery, unauthorized rejection and an actual routed
completion/stream. A local OpenAI-compatible fixture verifies the proxy path without
proving access to, model quality from, or billing behavior of a real provider.
