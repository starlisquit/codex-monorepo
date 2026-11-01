# NGINX and LiteLLM deployment verification — 2026-11-01

Repository update: the NGINX template and its Helm source have been removed.
The results below remain historical evidence; LiteLLM is still available.

Focused K3s play `6ae70b4c789ac234e334e7c2` started at 12:50 Europe/Istanbul
(09:50 UTC), after destruction of the security validation play. Only NGINX,
LiteLLM and a disposable local OpenAI-compatible backend were installed. No
database, Redis, Ceph, observability stack or security agents were deployed.
Kubernetes reported v1.37.1+k3s1. Templates were committed as `c72f7e6`; deployed
values and fixture SHA-256 hashes match the repository inputs in the
[machine-readable evidence](evidence/proxy-ai-2026-11-01.json).

## Official charts

| Component | Source | Chart / application |
| --- | --- | --- |
| NGINX Ingress Controller | https://helm.nginx.com/stable | nginx-ingress 2.8.0 / controller 5.7.0, open-source mode |
| LiteLLM | oci://ghcr.io/berriai/litellm-helm | litellm-helm 1.106.6 / application 1.106.6 |

The published OCI package, not the development branch's Chart.yaml, determined
LiteLLM's pinned version. Pulled chart digest:
`sha256:b681a4cb1eafd4c8aa642b58e9666d9f8afb9c4972d2230d91b2b1dfecf8f934`.

Both components have namespace resources, HelmReleases, pinned sources and
watch-labelled values ConfigMaps. They are opt-in and are not selected by the
full-platform overlay. NGINX provides class `nginx`, NodePorts, metrics and
streaming-friendly settings. LiteLLM defaults to a database-free static model
proxy with external master/provider credential Secrets and one worker.

## Checks and observed results

All 20 functional assertions passed initially and were repeated successfully
after replacing each deployment's Pod: 60 assertions across three runs.

| Check | Result |
| --- | --- |
| Local validation | 96 Kustomize builds; existing selected dependency/release checks; clean whitespace |
| Official chart validation | Both charts linted/rendered with repository values under Helm 3.17.0 and Helm 4.3.1; both live Helm releases deployed with Ready replicas |
| LiteLLM readiness | HTTP 200 through verified NGINX HTTPS |
| TLS identity | Client trusted the lab certificate and verified `litellm.validation.local`; untrusted CA and unknown TLS SNI rejected |
| Authentication | Missing key returned 401. Invalid key returned 400 with an error and no model data in database-free mode. Valid master key returned the configured model |
| Model routing | Completion reached the local backend as model `validation-model`; backend verified its provider credential and returned `proxy-route-verified`; usage value 5 propagated |
| Unknown model | Rejected with a client error rather than routed as a configured model |
| Streaming | SSE content and `[DONE]` propagated progressively. Final run: first content at 0.076 s, stream finished at 1.023 s; proxy buffering did not hold the whole response |
| HTTP redirect | HTTP entrypoint returned an HTTPS redirect; clients in the NodePort-only lab used the discovered HTTPS NodePort explicitly |
| Class isolation | Ingress with `ingressClassName: not-nginx` did not expose its route; request returned 404; temporary probe removed |
| Metrics | Internal NGINX Service returned Prometheus text including ingress resource and reload metrics; no ServiceMonitor dependency required |
| NGINX recovery | Replacement Pod had a new UID; route/certificate configuration reconciled and all 20 checks passed again |
| LiteLLM recovery | Replacement Pod had a new UID; the same external Secrets/config restored authentication and routing; all 20 checks passed again |

Pod Ready did not imply NGINX's application route was immediately reconciled:
the first immediate post-replacement attempt was transiently unsuccessful, then
the full suite passed after reconciliation. This is recovery evidence, not
zero-downtime or high-availability certification for a one-replica deployment.

At one healthy snapshot, LiteLLM used about 554 MiB, NGINX 22 MiB, and the fixture
11 MiB. These are bounded observations, not production sizing guarantees.

## Reproduction and limits

Use repository chart values plus the excluded lab examples:

- `flux/docs/runbooks/examples/proxy-ai-validation-values.yaml`
- `flux/docs/runbooks/examples/proxy-ai-validation-backend.yaml`

Provision lab-only master/provider Secrets and a temporary TLS Secret outside
Git. Discover HTTP/HTTPS NodePorts from the NGINX Service. Requests used the real
NGINX listener, correct Host/SNI, a verifying TLS context, `/health/readiness`,
`/v1/models` and `/v1/chat/completions`. NGINX metrics were checked through the
Kubernetes Service proxy. No TLS verification was disabled.

The local backend is a fixture, not a language model. No paid provider request,
real OpenAI credential, inference quality or provider billing was tested. The
default model route must be configured with the user's real provider credentials
before production. PostgreSQL/Redis, persistent virtual keys, budget/spend history,
admin UI, the excluded PostgreSQL example, public DNS/certificates and production
load balancer integration were not validated by this database-free test.

## Teardown

Findings were published as `533d455` and verified on both remotes before teardown.
At 13:05:44 Europe/Istanbul / 10:05:44 UTC, the destroy API returned `ok: true`
for play `6ae70b4c789ac234e334e7c2`; subsequent listing showed no running plays.
The playground was destroyed, not retained in a stopped state.
