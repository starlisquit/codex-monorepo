# Redis Insight and NUI browser verification — 2026-11-01

## Result

Both UIs passed the actual browser workflows described below, including a
repeat after replacing both application Pods. This supersedes the initial
[API-only findings and UI blockers](redis-nui-validation-2026-11-01.md).
NUI requires the committed compatibility fixes; the unmodified official image
still has the defects observed in the initial run.

The repeatable Chromium suite passed **16 assertions before and 16 after Pod
replacement**, with no JavaScript page errors or application API HTTP errors
in either successful run. Initial browser onboarding and resource creation
were exercised separately. Sanitized results, image IDs, Pod UIDs and deployed
input hashes are in [the evidence](evidence/redis-nui-ui-2026-11-01.json).

## Fresh focused playground

Playground `6ae71991789ac234e3366509` was created at
2026-11-01 10:50:57 UTC (13:50:57 Europe/Istanbul). Only Redis Insight, NUI,
a password-protected Redis fixture and a single NATS JetStream server were
installed, in addition to the K3s base services. Chromium ran on dev-machine.
No full-platform stack, Ceph or monitoring services were added.

Versions remained Redis Insight 3.8.0, NUI chart 0.1.6 / image 0.10.0,
NATS chart 2.15.2 and Redis fixture 8.2.2-alpine. NUI's multi-architecture image
is now pinned to digest
`sha256:879b64b2f2fa4c3298681ed0bebfbcfd80cae281ff787a10c404bbd62160d18a`.
The Redis Insight image was already pinned by digest. Official Redis Insight
installation still uses manifests: Redis does not publish an official chart.

## Browser workflows actually exercised

| UI | Browser actions | Independent confirmation |
| --- | --- | --- |
| Redis Insight setup | Completed the initial settings form, selected encryption, kept analytics/notifications disabled and submitted the test installation's terms checkbox | Setup screen disappeared and database list rendered |
| Redis Insight connection | Entered a password-protected Redis connection URL, clicked Test connection, observed success, saved and opened it | Browser entered the database key browser; password was obtained only from the disposable Secret |
| Redis Insight create | Selected String in Add key, entered a key and value, submitted and viewed the value | redis-cli read the browser-created key |
| Redis Insight read/edit | Searched for a key, opened it, read a CLI-written value, edited its value and applied the change | redis-cli read the exact edited value, before and after Pod replacement |
| Redis Insight preferences/reload | Saved tree sorting through the browser, reloaded and reopened the key browser | Settings save returned 200; onboarding did not recur |
| NUI connection | From an empty browser profile, clicked ALL / NEW, entered a name, added a HOST list entry and created the connection | Saved connection remained available to later fresh profiles and after Pod replacement |
| NUI stream creation | Created file-backed stream BROWSER_UI with subject browser.> through the UI | NATS CLI confirmed the stream subjects |
| NUI publishing | Opened Send message, entered a subject and JSON in Monaco, clicked SEND | NATS CLI read and decoded the stored message and matched its payload |
| NUI message browsing | Opened the stream's Messages view from a separate fresh browser profile | UI displayed both browser-published and independently CLI-published subjects |
| NUI first bucket | Opened an empty bucket list and created BROWSER_KV through the UI | Bucket appeared without the prior null-list JavaScript error |
| NUI KV create/read | Created an entry through the browser editor; separately wrote a value with the CLI and opened that key in the UI | CLI payload matched the browser write; browser Monaco content showed the CLI-written value |
| NUI session reload | Reloaded the page with a KV entry open | Saved browser session restored the entry detail without injected storage |
| Both UI Pod replacements | Deleted both UI Pods, waited for their replacements, restarted local port-forwards and reran the browser suite | New UIDs, retained saved connections and credentials, all 16 checks passed again |

The first draft of browser automation clicked NUI's text labels on compact
cards, but those controls render as icons. The final runner uses their actual
visible icon controls. Monaco uses its real textbox and keyboard events.
There is no browser localStorage seeding, application API mocking or test-only
JavaScript override. Each fresh-profile check creates a new browser context.
The browser obtains Redis credentials from its saved, encrypted connection;
the verification runner never posts application write requests directly.

## Deployment fixes

`flux/infrastructure/broker/nui/start.sh` is mounted from ConfigMap
`nui-startup` and runs before the official image entrypoint:

1. The compiled session loader calls JSON.parse on absent localStorage keys,
   obtaining null. The prior crash came from passing that null to the layout
   serializer. The patch retains the upstream right-hand drawer default and
   supplies empty arrays for absent/null session collections.
2. The empty KV-bucket endpoint serializes its list as null. NUI's bucket store
   then attempts to spread that value when creating its first bucket, raising
   `t.state.all is not iterable`. The patch normalizes that store response to
   an empty array. This was found through actual browser creation testing;
   earlier API checks could not detect it.
3. The wrapper retains the existing schema-path correction under persistent
   `/db`, avoiding the unwritable root-level schema directories.

The script changes the served JavaScript for every user; it is a local fix to
the official image, not a newly released upstream fix. It verifies the known
bundle fragments and refuses startup when they are absent. The image digest
and compatibility-patch Pod annotation make this coupling explicit. Review
both the script and the digest during upgrades, and bump the annotation when
changing the script so Helm rolls the Pod. The wrapper and values deployed in
the playground have SHA-256 hashes matching the committed repository inputs.

## Other findings

Redis Insight returns 404 for a database's settings resource before any
per-database preferences have been saved. The upstream repository explicitly
throws DATABASE_SETTINGS_NOT_FOUND for a missing settings entity. The normal
key browser continued to work. Saving tree sorting through the UI created the
settings with HTTP 200; both complete successful suite runs then recorded zero
application API errors. No broad error filter or whitelist was added to the
runner to conceal this response.

Redis Insight requires both a stable external RI_ENCRYPTION_KEY and explicit
selection of encryption in setup. The fresh playground used random Secrets
outside Git. Onboarding, including the terms checkbox, was completed only in
this disposable test installation. No provider account or subscription was
created. The production operator still completes their own installation setup.

No change to Redis Insight manifests was necessary for these browser flows;
its earlier incompleteness was a gap in verification. NUI needed code fixes
in the deployment wrapper. The original failed findings remain available as
historical evidence with a link to this corrected result.

## Reproduction

Use the repository templates and the isolated Redis backend example from the
initial findings. Supply the external encryption/password Secrets, enable
JetStream in a one-replica official NATS chart deployment, and use local-path
storage for this focused lab. Apply the NUI startup ConfigMap alongside its
chart values; it is part of the directory's Kustomize output.

In the browser, complete the setup and connection-creation steps above. Name
the NUI connection `ui-nats`, connect it to the lab's NATS Service, create stream
`BROWSER_UI` for `browser.>` and KV bucket `BROWSER_KV`. In Redis Insight create
string key `browser:redisinsight` and save tree preferences once. Forward the UI
Services to localhost. Install Playwright/Chromium on the separate dev machine
and run the committed verification runner with the appropriate local ports:

```sh
python verify-redis-nui-browser.py \
  --redis-url http://localhost:5540 \
  --nui-url http://localhost:31314 \
  --phase initial --output ui-initial.json
```

The runner is at `flux/runbooks/scripts/verify-redis-nui-browser.py` and requires
kubectl access to the documented disposable fixture namespace workloads.
It intentionally writes test keys/messages and must not target production data.
Delete only the UI Pods, wait for readiness, restart port-forwards to the
replacement Pods, and repeat using `--phase after-pod-replacement`. This verifies
persistent application state and the startup patch executing again.

Repository validation passed all 98 Kustomize builds and the existing 37
selected child definitions / 25 selected releases. The pinned NUI chart passed
Helm lint with final values; shell/Python syntax and whitespace checks passed.
The live chart deployment and mounted ConfigMap were tested directly, without
claiming full Flux controller reconciliation.

These results cover the browser workflows listed above. They do not certify
every optional product feature, real platform Valkey/NATS TLS integration,
public ingress authentication, backend failover, backups or production load.
NUI's chart remains experimental upstream; private administrator access is the
default. The isolated test uses password-protected Redis and plaintext NATS,
so production connection settings must still match their actual backends.

## Publication and teardown

Findings, fixes and browser evidence were published as `c3e1918`; both GitHub
and GitLab main commit IDs were verified equal before teardown. The explicit
destroy API returned `ok: true` for `6ae71991789ac234e3366509` at
2026-11-01 11:07:40 UTC (14:07:40 Europe/Istanbul). The playground was destroyed,
not stopped; the immediate listing reported it non-running while deletion
propagated.
