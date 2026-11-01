# Disposable infrastructure credential probes

Run as laborant on dev-machine after Flux bootstrap of this exact run folder.
These helpers are for fresh disposable labs, not production initialization or
credential rotation. Install Python3/PyYAML. Keep all private input files outside
Git with mode0600. Scripts print only sanitized results/fingerprints.

```sh
python3 backend.py /home/laborant/repo /home/laborant/repo/flux/clusters/20261101-235338-infra-eso-ci-2c2902
python3 contracts.py /home/laborant/repo/flux/clusters/20261101-235338-infra-eso-ci-2c2902
python3 verify.py
python3 capture.py /home/laborant/repo/flux/clusters/20261101-235338-infra-eso-ci-2c2902
```

The backend initializes one lab OpenBao replica, stores recovery material and
randomized application values in an owner-only VM directory, and applies the
actual template policy/role files. It creates only named disposable fixture
Secrets directly; application target Secrets must all be created by ESO.
The contracts check compares every delivered key/value, ownership, own-path
access and denial of unrelated paths/wrong audiences. Application probes use
actual workload APIs or executors. Capture exports only sanitized evidence.
Long-running tasks should run detached with protected logs, not inside a
short-lived remote-shell invocation. Preserve sanitized evidence before deleting
the playground; never export private state or raw application logs to Git.

CI input: `/home/laborant/gitlab-state.json` must contain `project_id`,
`runner_id`, `runner_token` and `renovate_token` from an authorized disposable
project runner/bot setup. Create an isolated temporary validation branch containing
`pipeline.gitlab-ci.yaml` as `.gitlab-ci.yml`, tagged `infra-eso-validation`.
The retained probe expects branch `infra-eso-validation-20261101`; adapt it for a
new run. Delete the temporary runner/branch after saving results. Never rotate
or revoke a supplied user's PAT as part of this cleanup.
