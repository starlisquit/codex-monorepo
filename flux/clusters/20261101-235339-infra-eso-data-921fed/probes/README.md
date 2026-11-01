# Disposable infrastructure credential probes

Run as laborant on dev-machine after Flux bootstrap of this exact run folder.
These helpers are for fresh disposable labs, not production initialization or
credential rotation. Install Python3/PyYAML. Keep all private input files outside
Git with mode0600. Scripts print only sanitized results/fingerprints.

```sh
python3 backend.py /home/laborant/repo /home/laborant/repo/flux/clusters/20261101-235339-infra-eso-data-921fed
python3 contracts.py /home/laborant/repo/flux/clusters/20261101-235339-infra-eso-data-921fed
python3 verify.py
python3 capture.py /home/laborant/repo/flux/clusters/20261101-235339-infra-eso-data-921fed
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

The local SeaweedFS S3 fixture is intentionally non-HA and ephemeral. Its storage
slot budget must permit both default and bucket collections. A signed request
wait ensures the S3 listener is available before creating the bucket. These tests
back up/restore only a disposable ConfigMap, not persistent volumes or an external
production bucket. Remove failed test Backup/Restore CRs before rerunning this
single-use verification against a reset fixture.
