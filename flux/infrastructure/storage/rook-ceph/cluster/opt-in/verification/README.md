# Optional Ceph write/read verification

Select this directory after the Ceph cluster and CSI controllers are ready.
The small RWO PVC uses ceph-block; its Job writes, syncs and reads a known marker.
Wait for Job ceph-storage-check to complete before storage-dependent workloads.
The existing storage-ready Flux Kustomization selects this directory and
retains that dependency gate. It is not included automatically with the Ceph
operator, CSI or cluster charts. Patch the storage class for other deployments.
A completed Job proves that run only; use a new Job name or deliberately
recreate it to verify a later storage change.
