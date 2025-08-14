### Project Name: OCP-V Event-Driven Disaster Recovery Automation Project

### **1. Project Goals and Three-Mode Architecture**

**Goal:**
This project aims to build a three-mode, highly automated OCP-V disaster recovery solution. It combines event-driven real-time synchronization, periodic proactive validation, and manually triggered disaster recovery capabilities to achieve near-real-time data synchronization, eventual consistency assurance, and one-click disaster recovery failover.

**Three-Mode Architecture:**

1.  **Mode One: Event-Driven Replication**
    *   **Core**: AAP Event-Driven Ansible (EDA) Controller.
    *   **Objective**: To automatically and in real-time synchronize underlying storage data and related metadata to the disaster recovery site by listening for PV (PersistentVolume), PVC (PersistentVolumeClaim), VolumeSnapshot, and VolumeSnapshotContent events within specified namespaces in the primary OpenShift cluster. This mode offers the fastest response and is the primary means of data synchronization.
2.  **Mode Two: Scheduled Proactive Sync**
    *   **Core**: AAP Workflow Scheduler.
    *   **Objective**: To periodically (e.g., hourly) perform a comprehensive scan and synchronization of all PVs, PVCs, VolumeSnapshots, and VolumeSnapshotContents within specified namespaces at the primary site. This serves as a supplement and validation to the event-driven mode, ensuring eventual data consistency and preventing data discrepancies due to lost events. **Additionally, this mode compares resources between the primary and DR sites and deletes resources that exist on the DR site but have been deleted from the primary site, ensuring an exact mirror of the DR environment.**
3.  **Mode Three: Manual Failover**
    *   **Core**: AAP Workflow.
    *   **Objective**: In the event of a disaster, an administrator manually triggers a standardized workflow to rebuild storage and restore application services at the disaster recovery site.

### **2. Core Concepts and Automation Architecture**

**Automation Architecture Diagram:**

**Mode One: Event-Driven Replication**
```mermaid
graph TD
    subgraph "Event Source"
        A["fa:fa-server Kubernetes API Server<br><div style='font-size:smaller; font-style:italic'>Primary OCP Cluster</div>"]
    end

    subgraph "Event Pipeline"
        B{"fa:fa-envelope-open-text K8s Events<br><div style='font-size:smaller; font-style:italic'>PV, PVC, VS, VSC<br>ADDED/MODIFIED/DELETED</div>"}
        C["fa:fa-route Python Event Forwarder<br><div style='font-size:smaller; font-style:italic'>Filters by Namespace</div>"]
        D["fa:fa-cogs AAP EDA Controller<br><div style='font-size:smaller; font-style:italic'>Receives Webhook</div>"]
    end

    subgraph "Decision & Actions"
        E{"fa:fa-code-branch Rulebook Evaluation"}
        
        subgraph "PV/PVC Actions"
            F["fa:fa-sync-alt Sync Data<br><div style='font-size:smaller; font-style:italic'>rsync</div>"]
            H["fa:fa-trash-alt Delete Data"]
        end
        
        subgraph "VolumeSnapshot Actions"
            S1["fa:fa-copy Sync Snapshot<br><div style='font-size:smaller; font-style:italic'>Metadata & Data</div>"]
            S2["fa:fa-eraser Delete Snapshot"]
        end
    end

    subgraph "DR Destination"
        G["fa:fa-database DR Storage"]
    end

    A -- Generates --> B
    B -- Watched by --> C
    C -- "HTTP POST" --> D
    D -- Triggers --> E

    E -- "PV/PVC<br>ADDED/MODIFIED" --> F --> G
    E -- "PV/PVC<br>DELETED" --> H
    E -- "VolumeSnapshot<br>ADDED" --> S1 --> G
    E -- "VolumeSnapshot<br>DELETED" --> S2

    classDef source fill:#cce5ff,stroke:#333,stroke-width:2px;
    classDef pipeline fill:#e0e0e0,stroke:#333,stroke-width:1.5px;
    classDef decision fill:#fff59d,stroke:#333,stroke-width:2px;
    classDef action_sync fill:#d4edda,stroke:#155724,stroke-width:2px,color:#155724;
    classDef action_delete fill:#f8d7da,stroke:#721c24,stroke-width:2px,color:#721c24;
    classDef storage fill:#d1ecf1,stroke:#0c5460,stroke-width:2px;

    class A source;
    class B,C,D pipeline;
    class E decision;
    class F,S1 action_sync;
    class H,S2 action_delete;
    class G storage;
```

**Mode Two: Scheduled Proactive Sync**
```mermaid
graph TD
    subgraph "Scheduler"
        A["fa:fa-clock CRON Job<br><div style='font-size:smaller; font-style:italic'>Triggers Hourly</div>"] --> B["fa:fa-play-circle Execute Workflow<br><div style='font-size:smaller; font-style:italic'>Periodic Sync</div>"];
    end

    subgraph "Execution Flow"
        subgraph "Phase 1: Sync Primary to DR"
            direction LR
            C["fa:fa-list-alt Get Resources<br><div style='font-size:smaller; font-style:italic'>From Primary OCP</div>"] --> D{"fa:fa-sync Loop & Sync"};
            D -- "PV/PVC" --> E["fa:fa-copy Sync Storage<br><div style='font-size:smaller; font-style:italic'>rsync & apply PV/PVC</div>"];
            D -- "VS/VSC" --> F["fa:fa-file-alt Sync Metadata<br><div style='font-size:smaller; font-style:italic'>Apply VS/VSC</div>"];
        end

        subgraph "Phase 2: Clean Stale Resources"
            direction LR
            G["fa:fa-list-alt Get Resources<br><div style='font-size:smaller; font-style:italic'>From DR OCP</div>"] --> H{"fa:fa-exchange-alt Compare<br><div style='font-size:smaller; font-style:italic'>Primary vs DR</div>"};
            H -- "Exists only in DR" --> I["fa:fa-trash-alt Delete Stale Resource"];
            H -- "Exists in both" --> J["fa:fa-check-circle No Action"];
        end

        subgraph "Phase 3: Reporting"
            K["fa:fa-file-invoice Generate Report<br><div style='font-size:smaller; font-style:italic'>Log Sync & Clean Results</div>"]
        end
    end

    B --> C;
    E --> G;
    F --> G;
    I --> K;
    J --> K;

    subgraph "Interacting Systems"
        PrimaryOCP["fa:fa-server Primary OCP"]
        DROCP["fa:fa-server DR OCP"]
    end

    C -- Reads from --> PrimaryOCP;
    E -- Writes to --> DROCP;
    F -- Writes to --> DROCP;
    G -- Reads from --> DROCP;
    I -- Writes to --> DROCP;

    classDef scheduler fill:#f2f2f2,stroke:#333,stroke-width:1.5px;
    classDef phase1 fill:#e1f5fe,stroke:#0288d1,stroke-width:1.5px;
    classDef phase2 fill:#ffecb3,stroke:#ff8f00,stroke-width:1.5px;
    classDef phase3 fill:#d1c4e9,stroke:#5e35b1,stroke-width:1.5px;
    classDef system fill:#b2dfdb,stroke:#00796b,stroke-width:2px;
    classDef delete fill:#f8d7da,stroke:#d9534f,stroke-width:1.5px;
    classDef no_action fill:#d4edda,stroke:#5cb85c,stroke-width:1.5px;

    class A,B scheduler;
    class C,D,E,F phase1;
    class G,H phase2;
    class I delete;
    class J no_action;
    class K phase3;
    class PrimaryOCP,DROCP system;
```

**Mode Three: Manual Failover**
```mermaid
graph TD
    subgraph "Initiation"
        Admin["fa:fa-user Administrator"] -- Triggers --> Start["fa:fa-play-circle Execute Failover Workflow"];
    end

    subgraph "Phase 1: Pre-Failover (Optional)"
        direction LR
        A["fa:fa-power-off Shut down VMs<br><div style='font-size:smaller; font-style:italic'>on Primary Site</div>"]
        B["fa:fa-lock Set Storage Read-Only<br><div style='font-size:smaller; font-style:italic'>on Primary Site</div>"]
    end

    subgraph "Phase 2: Restore on DR Site"
        C["fa:fa-download Download OADP Backup<br><div style='font-size:smaller; font-style:italic'>from S3</div>"]
        D["fa:fa-file-code Parse Definitions<br><div style='font-size:smaller; font-style:italic'>PV, PVC, etc.</div>"]
        E["fa:fa-check-double Verify Data<br><div style='font-size:smaller; font-style:italic'>on DR NFS</div>"]
        F["fa:fa-upload Apply OADP Restore<br><div style='font-size:smaller; font-style:italic'>Excluding Storage</div>"]
    end

    subgraph "Phase 3: Verification & Finalization"
        G["fa:fa-server Verify VM Status<br><div style='font-size:smaller; font-style:italic'>on DR OCP</div>"]
        H["fa:fa-broom Clean Up<br><div style='font-size:smaller; font-style:italic'>Temporary Files</div>"]
        I["fa:fa-file-alt Generate Report"]
    end

    Start --> A --> B --> C --> D --> E --> F --> G --> H --> I;

    classDef initiation fill:#cce5ff,stroke:#6c8ebf,stroke-width:2px;
    classDef pre_failover fill:#fff0c1,stroke:#ff8f00,stroke-width:1.5px;
    classDef restore fill:#d4edda,stroke:#5cb85c,stroke-width:1.5px;
    classDef verification fill:#e6e6e6,stroke:#5e35b1,stroke-width:1.5px;
    classDef critical_check fill:#ffe6cc,stroke:#d9534f,stroke-width:1.5px;

    class Admin,Start initiation;
    class A,B pre_failover;
    class C,D,F restore;
    class E,G critical_check;
    class H,I verification;
```

### **3. Ansible Project Structure Design (EDA Integration)**
```
ocp-v-dr-automation/
├── inventory/
│   └── hosts.ini                 # Host Inventory
├── group_vars/
│   ├── all.yml
│   └── ...
├── rulebooks/
│   └── ocp_dr_events.yml         # EDA rulebook, listens for PV and Snapshot events
├── roles/
│   ├── nfs_sync_on_event/        # Role: Responds to PV create/modify events, executes rsync
│   ├── nfs_delete_on_event/      # Role: Responds to PV delete events, deletes remote directory
│   ├── snapshot_sync_on_event/   # Role: Responds to Snapshot create events, syncs metadata
│   ├── snapshot_delete_on_event/ # Role: Responds to Snapshot delete events, cleans up metadata
│   ├── oadp_backup_parser/       # Role: (For DR) Parses OADP backups
│   ├── dr_storage_provisioner/   # Role: (For DR) Deploys PV/PVC on DR cluster
│   ├── oadp_restore_trigger/     # Role: (For DR) Executes OADP restore
│   └── periodic_storage_sync/    # Role: (For periodic tasks) Iterates and syncs all storage resources
└── playbooks/
    ├── event_driven/
    │   ├── handle_nfs_pv_sync.yml    # Playbook: (For EDA) Calls nfs_sync_on_event
    │   ├── handle_nfs_pv_delete.yml  # Playbook: (For EDA) Calls nfs_delete_on_event
    │   ├── handle_snapshot_sync.yml  # Playbook: (For EDA) Calls snapshot_sync_on_event
    │   └── handle_snapshot_delete.yml# Playbook: (For EDA) Calls snapshot_delete_on_event
    ├── manual_dr/
    │   └── execute_failover.yml      # Playbook: (For DR) Executes a complete disaster recovery failover
    └── scheduled/
        └── execute_periodic_sync.yml # Playbook: (For periodic tasks) Executes a complete periodic synchronization
```
### **4. Mode One: Event-Driven Data Replication Logic Explained**

#### 4.1 OCP Event Forwarding and Webhook Trigger

*   **Implementation**: Achieved on the primary OpenShift cluster via a custom **Python Event Forwarder (k8s_event_forwarder.py)**.
    *   The forwarder runs as a Deployment within the cluster, using an `in-cluster` Service Account for authentication.
    *   The container image is built based on Red Hat UBI 8 (`registry.access.redhat.com/ubi8/python-39`), ensuring environment stability and security.
    *   **Configurable Namespaces**: The forwarder is configured with a list of namespaces to monitor via the `WATCH_NAMESPACES` environment variable. If the list is empty, it monitors all namespaces.
    *   It uses the `watch` feature of the `kubernetes` Python client to simultaneously monitor four types of resources:
        *   `PersistentVolume` (not namespaced)
        *   `PersistentVolumeClaim` (namespaced)
        *   `VolumeSnapshot` (namespaced)
        *   `VolumeSnapshotContent` (not namespaced)
    *   When an `ADDED`, `MODIFIED`, or `DELETED` event is captured, for namespaced resources, it checks if the resource belongs to a monitored namespace. If it matches, it wraps the event into a unified JSON payload (including the resource's `namespace` info) and sends it via an HTTP POST request to the Webhook URL configured on the AAP EDA Controller.
*   **Trigger Conditions**:
    *   **PersistentVolume**: Listens for all events on `v1.PersistentVolume` resources.
    *   **PersistentVolumeClaim**: Listens for events on `v1.PersistentVolumeClaim` resources in specified namespaces.
    *   **VolumeSnapshot**: Listens for events on `VolumeSnapshot` resources in the `snapshot.storage.k8s.io/v1` group in specified namespaces.
    *   **VolumeSnapshotContent**: Listens for events on `VolumeSnapshotContent` resources in the `snapshot.storage.k8s.io/v1` group.

#### 4.2 AAP EDA Rulebook and Logic Distribution

*   **File**: `rulebooks/ocp_dr_events.yml`
*   **Logic Design**:
    This rulebook listens for HTTP POST requests from the OCP event forwarder via `ansible.eda.webhook`. It defines a series of rules to trigger different AAP job templates based on the event type (`ADDED`, `MODIFIED`, `DELETED`) and resource type (`PersistentVolume`, `PersistentVolumeClaim`, `VolumeSnapshot`, `VolumeSnapshotContent`).
    - **Core Variable**: `watched_namespaces` is used to define the list of namespaces to monitor.
    - **Rule Categorization**:
        - **Non-namespaced resources (PV, VSC)**: Directly handle their create, modify, and delete events.
        - **Namespaced resources (PVC, VS)**: Before processing an event, check if the resource's namespace is in the `watched_namespaces` list.
    - **Trigger Action**: When a rule matches, it calls the `run_job_template` action, passing the resource object from the event (`event.resource`) as `extra_vars` to the corresponding AAP job template (e.g., "EDA - Sync PV to DR" or "EDA - Delete PVC from DR"), thus starting the subsequent sync or cleanup process.
    - **Special Handling for Snapshots**: For `VolumeSnapshot` creation events, the rule adds a condition to check `status.readyToUse == true`, ensuring the sync is triggered only when the snapshot is available.
*   **Corresponding Playbooks**:
    *   Playbooks should now be more generic to handle different types of resource objects. For example, there could be a common `handle_resource_sync.yml` and `handle_resource_delete.yml` that receive a `resource_object` variable and call different roles or execute different logic based on `resource_object.kind`.
    *   **playbooks/event_driven/handle_resource_sync.yml**:
        1.  Receives the `resource_object` variable from AAP EDA.
        2.  Calls the appropriate sync role based on `resource_object.kind` (e.g., "PersistentVolume", "PersistentVolumeClaim").
        3.  Role logic: Parses the incoming `resource_object` and performs data and metadata synchronization.
    *   **playbooks/event_driven/handle_resource_delete.yml**:
        1.  Receives the `resource_object` variable.
        2.  Calls the appropriate deletion role based on `resource_object.kind`.
        3.  Role logic: Parses the incoming `resource_object` and performs cleanup operations on the DR side.

### **5. Mode Two: Periodic Proactive Sync Logic Explained**

This process is triggered periodically by the AAP Scheduler, for example, every hour, serving as a supplement and validation for the event-driven mode.

*   **Playbook**: `playbooks/scheduled/execute_periodic_sync.yml`
*   **Core Role**: `roles/periodic_storage_sync`
*   **Key Variable**: The playbook should specify the namespaces to sync via the `target_namespaces` variable (e.g., `['ns1', 'ns2']`).

#### 5.1 Get All Relevant Resources
*   Connect to the primary OpenShift cluster (`ocp_primary`).
*   Using the `k8s_info` module, iterate through the `target_namespaces` list to get lists of `PersistentVolumeClaim` and `VolumeSnapshot` for each namespace.
*   Using the `k8s_info` module, get lists of all related `PersistentVolume` and `VolumeSnapshotContent` (these are non-namespaced but can be filtered by their associated PVCs and VolumeSnapshots).

#### 5.2 Iterate and Sync PVC/PV (Warm Standby)
*   In the playbook, use a `loop` to iterate through the retrieved list of PVCs.
*   For each PVC, find its bound PV (`spec.volumeName`).
*   Call the `periodic_storage_sync` role, passing the PVC and PV objects.
*   **Role Logic (`periodic_storage_sync`)**:
    *   **Input**: `pvc_object` and `pv_object`.
    *   **Step 1: Data Sync**: `delegate_to` the primary NFS server and execute `rsync` to sync data to the DR NFS server. **Note**: This requires key-based passwordless SSH login from the primary NFS server (`primary_nfs_server`) to the DR NFS server (`dr_nfs_server`).
    *   **Step 2: Modify PV Definition**: In memory, modify the `pv_object` definition, pointing its `spec.nfs.server` to the DR NFS server (`dr_nfs_server`). Also, forcibly set `spec.persistentVolumeReclaimPolicy` to `Retain` to prevent the PV status from failing on the DR side due to a missing delete plugin.
    *   **Step 3: Clean and Apply PV/PVC**:
        *   **Clean Metadata**: Before applying to the DR cluster, you must clean source-cluster-specific metadata from the PV and PVC objects. This includes `metadata.resourceVersion`, `metadata.uid`, `metadata.creationTimestamp`, `metadata.annotations`, the `status` field, and `spec.claimRef` in the PV. Removing `claimRef` allows the PV on the DR side to be bound by a new PVC.
        *   **Apply to DR Cluster**: Use the `kubernetes.core.k8s` module to connect to the DR OpenShift cluster (`ocp_dr`) via `ocp_dr_api_server` and `ocp_dr_api_key` variables, then `apply` the cleaned and modified PV definition and the cleaned PVC definition to the cluster.
    *   **Log Status**: Record the deployment status of each PV and PVC on the DR cluster.
    *   **Note**: This "Warm Standby" mode means storage resources are pre-created on the DR side, thus reducing recovery time.

#### 5.3 Iterate and Sync VolumeSnapshot/VolumeSnapshotContent
*   This functionality is now implemented to sync snapshot metadata to the DR site.
*   The playbook uses a `loop` to iterate through the retrieved `VolumeSnapshot` list.
*   For each `VolumeSnapshot` (where `status.readyToUse == true`), find its bound `VolumeSnapshotContent` (`status.boundVolumeSnapshotContentName`).
*   Call the `periodic_storage_sync` role, passing `snapshot_object` and `content_object` variables.
*   **Role Logic**:
    *   **Input**: `snapshot_object` and `content_object`.
    *   **Core Function: Metadata Sync**: The primary task of this role is to synchronize Kubernetes resource objects, ensuring the DR cluster is aware of these snapshots.
    *   **Clean Metadata**: Before applying to the DR cluster, the role cleans source-cluster-specific metadata from the `VolumeSnapshot` and `VolumeSnapshotContent` objects. This includes `metadata.resourceVersion`, `metadata.uid`, `metadata.creationTimestamp`, `metadata.annotations`, and the `status` field.
    *   **Apply to DR Cluster**: Use the `kubernetes.core.k8s` module to `apply` the cleaned `VolumeSnapshot` and `VolumeSnapshotContent` definitions to the DR OpenShift cluster.
    *   **Data Sync Note**: The current implementation focuses on metadata synchronization. The underlying snapshot data (e.g., the actual data in the `.snapshot` directory on NFS) is assumed to be synchronized by other storage-level mechanisms (like storage array replication or custom logic with `rsync`). The Ansible role itself does not perform an `rsync` of the snapshot data.

#### 5.4 Clean Stale Resources on DR Site
*   After syncing all resources from the primary site, the playbook performs a reverse check.
*   It fetches all relevant resources (PV, PVC, VolumeSnapshot, VolumeSnapshotContent, etc.) from the specified namespaces on the DR site.
*   It compares the list of resources from the DR site with the list from the primary site.
*   If a resource is found on the DR site but not on the primary site, it is considered stale (deleted from primary) and will be deleted from the DR site.
*   All deletion operations are logged.

#### 5.5 Generate Report
*   At the end of the playbook, summarize the synchronization and cleanup results for all resources.
*   Generate a concise report indicating which resources were synced successfully, which failed, and which were cleaned up. This report can be sent to administrators via email, webhook, etc.

### **6. Mode Three: Manual Disaster Recovery Logic Explained**

This process is manually initiated by an administrator via an AAP Workflow Template after a disaster occurs.

#### 6.1 Pre-Failover Actions (Primary Site)

*   **Objective**: Ensure data consistency and prepare for disaster recovery during a primary site failure or planned switchover.
*   **Implementation**: As initial steps in the `manual_dr/execute_failover.yml` playbook.
*   **Roles/Tasks**:
    1.  **Shut down relevant VMs on the primary site**:
        *   Connect to the primary OpenShift cluster (ocp_primary).
        *   Identify all virtual machines in the protected namespaces.
        *   Execute `oc delete vm <vm-name> -n <namespace>` or `oc patch vm <vm-name> -p '{"spec":{"running":false}}' --type=merge` to shut down the VMs.
    2.  **(Optional) Set primary storage to read-only**:
        *   For NFS scenarios, connect to the primary NFS server.
        *   Modify the NFS export configuration to set the relevant paths to read-only, preventing further writes.
        *   **Note**: This step needs to be adjusted based on the actual storage type and automation capabilities.

#### 6.2 Find and Parse Backup

*   **Role: oadp_backup_parser**
    1.  **Input**: The `backup_name` to restore (provided by an AAP Survey; if empty, finds the latest) and `namespace`.
    2.  Executes on `localhost`.
    3.  Downloads the specified OADP backup package from S3.
    4.  Unzips and parses it, extracting all PV, PVC, VolumeSnapshot, and VolumeSnapshotContent JSON definitions into `pv_info_list`, `pvc_info_list`, `vs_info_list`, and `vsc_info_list` variables.
    5.  **Output**: List variables containing all parsed resource definitions.

#### 6.3 Storage Logic Dispatch and Validation (NFS Scenario)

*   **Playbook Internal Logic**:
    1.  **Input**: The `pv_info_list` from the previous step.
    2.  **Logic Dispatch**: Use a `when` condition or the `when` clause of `include_role` to decide which storage type's validation logic to execute based on `item.spec.storageClassName`.
    3.  **NFS Validation**: **On the DR site's NFS server (`delegate_to: dr_nfs_server`)**, perform data validation. This step no longer performs data synchronization but is simplified to check if the data directory exists on the DR side.
        *   Based on the path information for each PV in `pv_info_list`, check if the corresponding directory has been created on the DR NFS server.
        *   If a directory does not exist, log a warning or error, indicating a potential issue with the periodic sync.

#### 6.4 Restore Applications on DR OCP

*   **Role: oadp_restore_trigger**
    1.  **Input**: `backup_name`.
    2.  Connects to the DR OCP cluster (`ocp_dr`).
    3.  Dynamically generates a Restore object, setting `spec.backupName` to the input `backup_name`, and `excludedResources` must include `persistentvolumes`, `persistentvolumeclaims`, `volumesnapshots`, `volumesnapshotcontents`.
    4.  `apply` this Restore object and poll the VM status until successful.

#### 6.5 Post-Disaster Recovery Validation and Cleanup

*   **Objective**: Confirm successful disaster recovery and perform necessary cleanup tasks.
*   **Implementation**: As subsequent steps in the `manual_dr/execute_failover.yml` playbook.
*   **Roles/Tasks**:
    1.  **Verify VM Status**:
        *   Connect to the DR OpenShift cluster (`ocp_dr`).
        *   Check if the restored virtual machines are in the `Running` state.
        *   Attempt to connect inside the VMs to verify that application services have started correctly.
    2.  **Clean Up Temporary Files**:
        *   Delete the temporary backup files downloaded and unzipped by the `oadp_backup_parser` role.
    3.  **Generate Report**:
        *   Record the time of the failover, its duration, success or failure status, and any critical information.

### **7. AAP Platform Configuration**

1.  **EDA Controller Configuration**:
    *   Create a Project pointing to the Git repository containing the `rulebooks/` directory.
    *   Configure a Decision Environment (usually the default one).
    *   Create a Rulebook Activation, associate it with the project and the `ocp_dr_events.yml` rulebook, and enable it.
    *   **Important**: In the Rulebook Activation, the Webhook URL and authentication Token must be passed as environment variables to the `k8s_event_forwarder.py` Deployment.
2.  **Workflow and Scheduling Configuration**:
    *   **Event-Driven Job Templates**: Create Job Templates for the playbooks triggered by EDA, such as `handle_nfs_pv_sync.yml`, `handle_nfs_pv_delete.yml`, etc.
    *   **Periodic Sync Job Template**: Create a Job Template associated with the `scheduled/execute_periodic_sync.yml` playbook.
        *   Configure a **Schedule** on this Job Template with a CRON expression (e.g., `0 * * * *` for hourly execution).
    *   **Manual Recovery Workflow Template**: Create a "One-Click Failover" Workflow Template, associate it with the `manual_dr/execute_failover.yml` playbook, and configure a survey to receive the `backup_name`.

With this design, your disaster recovery solution will be elevated to a new level, achieving automated and real-time data synchronization, ensuring eventual consistency through periodic validation, while maintaining the rigor and controllability of the disaster recovery process.
