# Shared platform namespaces

Optional namespace bundle for the existing platform components. It creates
namespaces only, not workloads. Full-platform clusters can select this
bundle once in their foundation rather than duplicating the namespace YAML.
Smaller installations may provision only the namespaces they actually select.
Keep a namespace under one intended reconciliation owner when composing a new
cluster; some existing standalone components also declare their own namespace.
