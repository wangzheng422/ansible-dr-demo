# OCP-V DR Automation - Modification Record

## 2025-08-25

*   **File Modified**: `planning/ansible-dr-design.md`
*   **Change Summary**:
    *   Updated the Ansible project structure to support multiple `StorageClass` types.
    *   Refactored the architecture to decouple the processing logic for PersistentVolumes (PVs)/PersistentVolumeClaims (PVCs) from VolumeSnapshots.
    *   Introduced storage-class-specific handling within roles for both event-driven and periodic synchronization modes. This allows for different data sync and metadata processing logic based on the underlying storage technology (e.g., `nfs-subdir`, `nfs-dynamic`).
    *   Separated Ansible playbooks and roles for PV/PVC management and Snapshot management to improve modularity and extensibility.

*   **Files Modified**: `ocp-v-dr-automation/` (multiple files)
*   **Change Summary**:
    *   **Playbooks**:
        *   Renamed and updated `playbooks/event_driven/handle_nfs_pv_*.yml` to `handle_pv_pvc_*.yml`.
        *   Updated all event-driven playbooks (`handle_pv_pvc_sync.yml`, `handle_pv_pvc_delete.yml`, `handle_snapshot_sync.yml`, `handle_snapshot_delete.yml`) to call new, dedicated roles.
        *   Updated the periodic sync playbook (`playbooks/scheduled/execute_periodic_sync.yml`) to call separate roles for PV/PVC sync (`periodic_pv_pvc_sync`) and snapshot sync (`periodic_snapshot_sync`).
    *   **Roles**:
        *   Created new role structure for event-driven actions: `event_pv_pvc_sync`, `event_pv_pvc_delete`, `event_snapshot_sync`, `event_snapshot_delete`.
        *   Created new role structure for periodic sync actions: `periodic_pv_pvc_sync`, `periodic_snapshot_sync`.
        *   Implemented a dispatch logic within the `main.yml` of PV/PVC-related roles to dynamically include tasks based on the `storageClassName` of the resource.
        *   Created placeholder task files for `nfs-subdir` and `nfs-dynamic` storage classes.
