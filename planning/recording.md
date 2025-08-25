# OCP-V DR Automation - Modification Record

## 2025-08-25

*   **File Modified**: `planning/ansible-dr-design.md`
*   **Change Summary**:
    *   Updated the Ansible project structure to support multiple `StorageClass` types.
    *   Refactored the architecture to decouple the processing logic for PersistentVolumes (PVs)/PersistentVolumeClaims (PVCs) from VolumeSnapshots.
    *   Introduced storage-class-specific handling within roles for both event-driven and periodic synchronization modes. This allows for different data sync and metadata processing logic based on the underlying storage technology (e.g., `nfs-subdir`, `nfs-dynamic`).
    *   Separated Ansible playbooks and roles for PV/PVC management and Snapshot management to improve modularity and extensibility.
