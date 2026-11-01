# Central PKI: Hubble and ClickHouse operator — 2026-11-01

Verified on fresh kubeadm playground `6ae791f87f32053bde29d303`, using Flux path
`./flux/clusters/20261101-222440-pki-network-29d303` and configuration revision
`c3d52c878f9f6c64bc4efbeb103d155ce308d005`. No separate Envoy Gateway controller
was installed. Only Cilium/Hubble, cert-manager, trust-manager, monitoring CRDs,
ClickHouse operator and disposable TLS probes were deployed.

Versions: Cilium 1.20.4, ClickHouse operator chart 0.0.8, cert-manager v1.21.3,
trust-manager v0.26.0, Flux v2.10.0, Hubble CLI v1.20.2, cmctl v2.6.2.

## Changes

- Hubble uses the chart's native `certmanager` certificate method and explicit
  ClusterIssuer `platform-workload-ca`, replacing Helm-generated certificates.
- ClickHouse operator sets `certManager.issuerRef` to the same ClusterIssuer,
  replacing the chart's fallback self-signed Issuer.
- The run waits for issuer and public trust distribution before these releases.
  It seeds Cilium with Hubble disabled before Flux exists, then enables the
  final configuration with run-only rollout flags. The lab additionally enables
  Hubble Relay serving TLS/mTLS; the base template's Relay listener default is
  otherwise unchanged. Hubble node/Relay-client certificates are centralized
  in the shared template.

## Actual verification

All six serving targets verified against the public central root and their
expected DNS names with TLS 1.3: three Hubble node endpoints, Hubble Relay,
ClickHouse admission webhook and ClickHouse authenticated metrics endpoint.
All rejected wrong-CA and wrong-hostname probes. Hubble nodes and Relay also
rejected clients lacking certificates. Root private key material was never
exported; only the required leaf client credential was used by the CLI.

The Hubble CLI made real, verified mTLS RPCs through Relay, reported **3/3 nodes
connected**, and returned flow messages from cplane-01, node-01 and node-02.
This proves Relay-to-node communication as well as a TLS handshake to Relay.

Both validating and mutating ClickHouse webhook CA bundles matched the central
public root's SHA-256 fingerprint. Kubernetes server-side admission dry runs
succeeded for KeeperCluster and ClickHouseCluster through those webhooks.
No managed ClickHouse data cluster was needed for these operator PKI checks.

Manually renewed all three Hubble certificates and both ClickHouse operator
certificates with cmctl. Every serving endpoint presented a **different serial**
after renewal, while the root fingerprint stayed unchanged. Client credential
refresh, Hubble status/flows and webhook admission all passed again. Certificate
revisions advanced to at least 2. Cilium, Relay and ClickHouse operator Pod UIDs
were unchanged: certificates hot-reloaded without workload restarts.

[Sanitized before/after evidence](evidence/central-pki-network-2026-11-01.json)
records issuer refs, TLS failures, serials, CA fingerprints, admission and RPC
results. Probe manifests/scripts are retained under this run's `probes/`.

## Scope

This verifies a fresh centralized deployment and leaf renewal. It does not claim
an unattended in-place handover from a previously running, independent CA, or
that ClickHouse database listeners were enabled for TLS. Kubernetes/bootstrap PKI
remains separate. The legacy central-root CN `openbao-injector-ca` is preserved;
OpenBao is not the signing backend. cert-manager signs through the CA ClusterIssuer.

## Teardown

Publish findings and configuration to both remotes before destroying this
playground; confirmed destruction will be recorded afterwards.
