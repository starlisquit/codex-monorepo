# Repository workflow

Keep GitHub (`origin`) and GitLab (`gitlab`) synchronized. Fetch both before
publishing, preserve remote changes, push the same commits to `main` on both,
and verify their remote commit IDs match. Never commit credentials.

Use focused iximiuz Labs playgrounds containing only the components needed for
each validation. Multiple playgrounds are allowed. When a playground has served
its purpose, commit findings and configuration updates to both remotes, then
destroy it. Do not retain unused playgrounds in a stopped state.

For every new playground run, create a new folder under flux/clusters with
runbooks/scripts/new-validation-run.py and the playground ID. Never reuse an
old run folder. Bootstrap Flux against that exact folder, selecting only needed
namespace/source bases and workloads. Preserve completed run configurations and
findings, then destroy the playground after publishing to both remotes.
