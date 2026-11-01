# Infrastructure ESO: LiteLLM and SonarQube

**Passed.** Fresh K3s playground `6ae7a6cf7f32053bde2c28d0`, created alongside
three other focused infrastructure runs. Flux path:
`flux/clusters/20261101-235335-infra-eso-apps-2c28d0`.
Application tests completed **2026-11-02 00:07:51 Europe/Istanbul**
(2026-11-01 21:07:51 UTC). Tested workload/policy correction: `b394d1e`.

## Actual application results

Four real target Secrets were delivered from the supplied OpenBao KV paths by
the three application-specific opt-ins. Every provider property matched its
Kubernetes Secret, and each Secret had the correct ExternalSecret owner.
Own-path access worked; unrelated KV reads and wrong token audiences were denied.

- LiteLLM chart/image1.106.6 loaded `litellm-auth:master-key` and the provider
  `OPENAI_API_KEY`. Unauthenticated model discovery returned **HTTP401**;
  master-key-authenticated discovery listed the configured validation model.
  A real authenticated chat request traversed LiteLLM to the credential-checking
  local OpenAI-compatible fixture and returned `proxy-route-verified`.
- The `salt-key` property was also synced correctly. This run used LiteLLM's base
  database-free mode, so it does not claim persistent encrypted virtual-key or
  salt-key feature coverage; that feature's CNPG credentials remain separate.
- SonarQube Community Build26.9.0.129388/chart2026.5.1003 loaded its actual
  monitoring passcode from `sonarqube-monitoring`. The health endpoint rejected
  unauthenticated access and accepted `X-Sonar-Passcode` with the ESO value.
- The separate `external-database-secrets` opt-in delivered
  `sonarqube-database:password`. SonarQube used that credential against the
  disposable PostgreSQL18.6 fixture, became UP and created/retrieved a project.
  An independent authenticated PostgreSQL query confirmed persisted project data.
  This deliberately tests the external-database mode, not CNPG; no CNPG-generated
  credential was claimed by ESO.

## Runtime correction

Initial policies for all nine infrastructure opt-ins disabled the default OpenBao
policy but omitted ESO's required `auth/token/lookup-self` permission. Provider
validation failed with HTTP403/InvalidProviderConfig. The correction permits only
self-token lookup/renew/revoke, retaining exact-path read-only KV permissions.
After applying those backend policies, all four Secrets synced and the actual
application operations above passed. Routine validation enforces that complete
policy contract so this omission does not silently recur.

## Evidence and scope

[Sanitized evidence](evidence/infra-eso-apps-2026-11-01.json) records hashes,
contract/auth checks, successful application operations, versions, workload Pod
IDs and Flux source revisions. All selected HelmReleases were Ready at capture;
Flux stage metadata separately records later report/other-lane revision propagation.
Setup and probe scripts remain in this run folder.

OpenBao2.7.2/chart0.30.6, ESO2.14.0, cert-manager1.21.3 and trust-manager0.26.0
ran on K3s `v1.37.1+k3s1`. Only relevant prerequisites, applications and fixtures
were installed. OpenBao used one disposable 1Gi local-path replica with lab-only
recovery custody. Credential values, tokens, root/unseal material and private
keys were kept out of Git.

No real model/provider API, billing, Sonar analysis, browser suite, HA, backup or
CA rotation was tested here. PostgreSQL was an isolated password-authenticated
fixture; this does not verify TLS for the external-database deployment mode.
The existing centrally signed CNPG TLS tests remain documented separately.

## Teardown

Publish this report/configuration to both remotes before destroying this verified
playground. Record confirmed destruction afterwards.
