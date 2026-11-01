# Optional configuration

Explicitly select this Kustomization only after configuring a writable Velero backup location. It creates the metadata-only smoke Backup and does not back up PVC data. The default Velero template does not include it.
