### 项目名称：OCP-V 事件驱动灾备自动化项目

### **1. 项目目标与三模架构**

目标：  
本项目旨在构建一个三模式、高度自动化的 OCP-V 灾备解决方案。它结合了事件驱动的实时同步、周期性的主动校验和手动触发的灾备恢复能力，以实现数据近实时同步、最终一致性保障和一键式灾备切换。  
**三模架构：**

1. **模式一：事件驱动的实时数据复制 (Event-Driven Replication)**  
   * **核心**：AAP Event-Driven Ansible (EDA) Controller。  
   * **目标**：通过监听主 OpenShift 集群的 PV（PersistentVolume）事件，自动、实时地将底层存储数据同步到灾备站点。此模式响应速度最快，是数据同步的主要手段。
2. **模式二：周期性的主动同步 (Scheduled Proactive Sync)**
   * **核心**：AAP Workflow Scheduler。
   * **目标**：定时（例如每小时）对主站点的所有 PV 和 VolumeSnapshot 进行全面扫描和同步，作为事件驱动模式的补充和校验，确保数据最终一致性，防止因事件丢失导致的数据差异。
3. **模式三：手动触发的灾备恢复 (Manual Failover)**  
   * **核心**：AAP Workflow。  
   * **目标**：在发生灾难时，由管理员手动触发一个标准化的工作流，在灾备站点重建存储并恢复应用服务。

### **2\. 核心理念与自动化架构**

**自动化架构图：**

**模式一: 事件驱动的实时复制 (Event-Driven Replication)**
```mermaid
graph TD
    A[Primary OCP Cluster] --> B{PV & VolumeSnapshot Events<br>ADDED/MODIFIED/DELETED};
    B --> C[Python Event Forwarder<br>in-cluster deployment];
    C -- HTTP POST --> D[AAP EDA Controller<br>ansible.eda.webhook];
    D --> E{Rulebook Matches Condition};
    E -- PV ADDED/MODIFIED --> F[Trigger rsync on Primary NFS];
    F --> G[DR NFS Server];
    E -- PV DELETED --> H[Trigger Delete on DR NFS];
    E -- VolumeSnapshot ADDED --> S1[Sync Snapshot Metadata];
    E -- VolumeSnapshot DELETED --> S2[Delete Snapshot Metadata];

    style A fill:#cce5ff,stroke:#333,stroke-width:2px
    style B fill:#cce5ff,stroke:#333,stroke-width:2px
    style C fill:#cce5ff,stroke:#333,stroke-width:2px
    style D fill:#cce5ff,stroke:#333,stroke-width:2px
    style E fill:#cce5ff,stroke:#333,stroke-width:2px
    style F fill:#cce5ff,stroke:#333,stroke-width:2px
    style G fill:#cce5ff,stroke:#333,stroke-width:2px
    style H fill:#cce5ff,stroke:#333,stroke-width:2px
    style S1 fill:#cce5ff,stroke:#333,stroke-width:2px
    style S2 fill:#cce5ff,stroke:#333,stroke-width:2px
```

**模式二: 周期性的主动同步 (Scheduled Proactive Sync)**
```mermaid
graph TD
    subgraph AAP Controller
        A[Scheduler<br>CRON Job] -- Triggers Hourly --> B[Execute Periodic Sync Workflow];
    end

    subgraph Ansible Execution
        B --> C[Playbook: execute_periodic_sync.yml];
        C --> D[Get All PVs & Snapshots<br>from Primary OCP];
        D --> E{Loop through each PV};
        E -- NFS PV --> F[Role: periodic_storage_sync<br>Execute rsync for PV directory];
        D --> G{Loop through each Snapshot};
        G --> H[Role: periodic_storage_sync<br>Sync Snapshot Metadata];
        C --> I[Log Results & Generate Report];
    end

    subgraph Storage
        F --> J[DR NFS Server];
        H --> K[DR Metadata Store];
    end

    style A fill:#e1e1e1,stroke:#333,stroke-width:2px
    style B fill:#e1e1e1,stroke:#333,stroke-width:2px
    style C fill:#e6f7ff,stroke:#333,stroke-width:2px
    style D fill:#e6f7ff,stroke:#333,stroke-width:2px
    style E fill:#e6f7ff,stroke:#333,stroke-width:2px
    style F fill:#e6f7ff,stroke:#333,stroke-width:2px
    style G fill:#e6f7ff,stroke:#333,stroke-width:2px
    style H fill:#e6f7ff,stroke:#333,stroke-width:2px
    style I fill:#e6f7ff,stroke:#333,stroke-width:2px
    style J fill:#d4edda,stroke:#333,stroke-width:2px
    style K fill:#d4edda,stroke:#333,stroke-width:2px
```

**模式三: 手动灾备恢复 (Manual Failover)**
```mermaid
graph TD
    I[Administrator] --> J[Execute Failover Workflow];
    J --> K[Optional: Shut down VMs on Primary];
    K --> L[Optional: Set Primary Storage Read-Only];
    L --> M[Download OADP Backup from S3];
    M --> N[Parse PV/PVC Definitions];
    N --> O[Final Data Sync<br>rsync on DR NFS Server];
    O --> P[Apply Modified PVs/PVCs to DR OCP];
    P --> Q[Apply OADP Restore<br>exclude PV/PVC];
    Q --> R[Verify VM Status on DR OCP];
    R --> T[Clean Up Temporary Files];
    T --> U[Generate Report];

    style I fill:#d4edda,stroke:#333,stroke-width:2px
    style J fill:#d4edda,stroke:#333,stroke-width:2px
    style K fill:#d4edda,stroke:#333,stroke-width:2px
    style L fill:#d4edda,stroke:#333,stroke-width:2px
    style M fill:#d4edda,stroke:#333,stroke-width:2px
    style N fill:#d4edda,stroke:#333,stroke-width:2px
    style O fill:#d4edda,stroke:#333,stroke-width:2px
    style P fill:#d4edda,stroke:#333,stroke-width:2px
    style Q fill:#d4edda,stroke:#333,stroke-width:2px
    style R fill:#d4edda,stroke:#333,stroke-width:2px
    style T fill:#d4edda,stroke:#333,stroke-width:2px
    style U fill:#d4edda,stroke:#333,stroke-width:2px
```

### **3\. Ansible 项目结构设计 (集成 EDA)**
```
ocp-v-dr-automation/
├── inventory/
│   └── hosts.ini                 # 主机清单
├── group_vars/
│   ├── all.yml
│   └── ...
├── rulebooks/
│   └── ocp_dr_events.yml         # EDA 规则手册，监听PV和Snapshot事件
├── roles/
│   ├── nfs_sync_on_event/        # 角色: 响应PV创建/修改事件，执行rsync
│   ├── nfs_delete_on_event/      # 角色: 响应PV删除事件，删除远程目录
│   ├── snapshot_sync_on_event/   # 角色: 响应Snapshot创建事件，同步元数据
│   ├── snapshot_delete_on_event/ # 角色: 响应Snapshot删除事件，清理元数据
│   ├── oadp_backup_parser/       # 角色: (DR用) 解析OADP备份
│   ├── dr_storage_provisioner/   # 角色: (DR用) 在DR集群部署PV/PVC
│   ├── oadp_restore_trigger/     # 角色: (DR用) 执行OADP恢复
│   └── periodic_storage_sync/    # 角色: (周期性任务用) 遍历并同步所有存储资源
└── playbooks/
    ├── event_driven/
    │   ├── handle_nfs_pv_sync.yml    # Playbook: (EDA用) 调用nfs_sync_on_event
    │   ├── handle_nfs_pv_delete.yml  # Playbook: (EDA用) 调用nfs_delete_on_event
    │   ├── handle_snapshot_sync.yml  # Playbook: (EDA用) 调用snapshot_sync_on_event
    │   └── handle_snapshot_delete.yml# Playbook: (EDA用) 调用snapshot_delete_on_event
    ├── manual_dr/
    │   └── execute_failover.yml      # Playbook: (DR用) 执行完整的灾备切换
    └── scheduled/
        └── execute_periodic_sync.yml # Playbook: (周期性任务用) 执行完整的周期性同步
```
### **4\. 模式一：事件驱动数据复制逻辑详解**

#### 流程 1-2: OCP 事件转发与 Webhook 触发

* **实现方式**: 在主 OpenShift 集群上，通过一个定制的 **Python 事件转发器 (k8s_event_forwarder.py)** 来实现。
  * 该转发器作为一个 Deployment 运行在集群内部，使用 `in-cluster` Service Account 进行认证。
  * 它通过 `kubernetes` Python 客户端的 `watch` 功能，同时监视 `PersistentVolume` 和 `VolumeSnapshot` 两种资源。
  * 当捕获到资源的 `ADDED`, `MODIFIED`, 或 `DELETED` 事件时，它会将事件封装成一个统一的 JSON 载荷，通过 HTTP POST 请求发送到 AAP EDA Controller 上配置的 Webhook 地址。
* **触发条件**:
  * **PersistentVolume**: 监听 `v1.PersistentVolume` 资源的所有事件。
  * **VolumeSnapshot**: 监听 `snapshot.storage.k8s.io/v1` 组下的 `VolumeSnapshot` 资源的所有事件。

#### 流程 3-4: AAP EDA Rulebook 与逻辑分发

* **文件**: rulebooks/ocp_dr_events.yml  
* **逻辑设计**:
```yaml
---
- name: Process OCP DR Events from Webhook
  hosts: localhost
  sources:
    - ansible.eda.webhook:
        host: 0.0.0.0
        port: 5000
        # 在 AAP 中，需要配置 token 来保护此 webhook
        # token: "{{ eda_webhook_token }}"

  rules:
    # 规则 1: 处理 NFS PV 的创建和修改
    - name: Handle NFS PV Create or Update
      condition: >
        event.kind == "PersistentVolume" and
        (event.type == "ADDED" or event.type == "MODIFIED") and
        event.resource.spec.storageClassName == "nfs-dynamic"
      action:
        run_job_template:
          name: "EDA - Sync NFS PV to DR"
          organization: "Default"
          job_args:
            extra_vars:
              pv_object: "{{ event.resource }}" # 转发器封装的完整PV对象

    # 规则 2: 处理 NFS PV 的删除
    - name: Handle NFS PV Deletion
      condition: >
        event.kind == "PersistentVolume" and
        event.type == "DELETED" and
        event.resource.spec.storageClassName == "nfs-dynamic"
      action:
        run_job_template:
          name: "EDA - Delete NFS PV from DR"
          organization: "Default"
          job_args:
            extra_vars:
              pv_object: "{{ event.resource }}"

    # 规则 3: 处理 VolumeSnapshot 的创建
    - name: Handle VolumeSnapshot Creation
      condition: >
        event.kind == "VolumeSnapshot" and
        event.type == "ADDED" and
        event.resource.status.readyToUse == true
      action:
        run_job_template:
          name: "EDA - Sync VolumeSnapshot Metadata"
          organization: "Default"
          job_args:
            extra_vars:
              snapshot_object: "{{ event.resource }}"

    # 规则 4: 处理 VolumeSnapshot 的删除
    - name: Handle VolumeSnapshot Deletion
      condition: >
        event.kind == "VolumeSnapshot" and
        event.type == "DELETED"
      action:
        run_job_template:
          name: "EDA - Delete VolumeSnapshot Metadata"
          organization: "Default"
          job_args:
            extra_vars:
              snapshot_object: "{{ event.resource }}"
```
* **对应的 Playbooks**:
  * **playbooks/event_driven/handle_nfs_pv_sync.yml**:
    1. 接收 AAP EDA 传递过来的 `pv_object` 变量。
    2. 调用 `nfs_sync_on_event` 角色。
    3. 角色逻辑：仅调试传入的 `pv_object` 变量。所有路径构造和 `rsync` 逻辑均已注释。
  * **playbooks/event_driven/handle_nfs_pv_delete.yml**:
    1. 接收 `pv_object` 变量。
    2. 调用 `nfs_delete_on_event` 角色。
    3. 角色逻辑：仅调试传入的 `pv_object` 变量。所有路径构造和 `rsync` 逻辑均已注释。
  * **playbooks/event_driven/handle_snapshot_sync.yml**:
    1. 接收 `snapshot_object` 变量。
    2. 调用 `snapshot_sync_on_event` 角色。
    3. 角色逻辑：解析快照元数据，可能需要在灾备站点记录快照信息或触发其他相关操作。
  * **playbooks/event_driven/handle_snapshot_delete.yml**:
    1. 接收 `snapshot_object` 变量。
    2. 调用 `snapshot_delete_on_event` 角色。
    3. 角色逻辑：根据快照元数据，在灾备站点清理对应的记录或资源。

### **5\. 模式二：周期性主动同步逻辑详解**

此流程通过 AAP 的调度功能（Scheduler）定时触发，例如每小时执行一次，作为对事件驱动模式的补充和校验。

*   **Playbook**: `playbooks/scheduled/execute_periodic_sync.yml`
*   **核心角色**: `roles/periodic_storage_sync`

#### **流程详解**:

1.  **获取所有相关资源**:
    *   连接到主 OpenShift 集群 (`ocp_primary`)。
    *   使用 `k8s_info` 模块获取所有 `storageClassName` 为 `nfs-dynamic` 的 `PersistentVolume` 列表。
    *   使用 `k8s_info` 模块获取所有 `VolumeSnapshot` 列表。

2.  **遍历并同步 PV**:
    *   在 Playbook 中，使用 `loop` 循环遍历获取到的 PV 列表。
    *   对于每一个 PV，调用 `periodic_storage_sync` 角色。
    *   **角色逻辑 (`periodic_storage_sync`)**:
        *   **输入**: 单个 `pv_object`。
        *   **构造路径**: 从 `pv_object.spec.nfs.path` 提取源路径。目标路径可以基于源路径在灾备 NFS 服务器上生成。
        *   **执行同步**: `delegate_to` 到灾备 NFS 服务器 (`dr_nfs_server`)，执行 `rsync -av --delete` 命令，确保灾备端与主站点的目录完全一致。
        *   **记录日志**: 记录每个 PV 的同步状态（成功、失败、差异）。

3.  **遍历并同步 VolumeSnapshot**:
    *   同样使用 `loop` 循环遍历获取到的 `VolumeSnapshot` 列表。
    *   对于每一个快照，调用 `periodic_storage_sync` 角色（或一个专门处理快照的独立角色）。
    *   **角色逻辑**:
        *   **输入**: 单个 `snapshot_object`。
        *   **同步元数据**: 确保快照的元数据（例如创建时间、关联的 PV 等）在灾备站点的记录库中是最新的。
        *   **（可选）同步快照数据**: 如果底层存储支持基于快照的增量同步，则触发相应的同步命令。对于 NFS，这通常意味着同步与快照关联的特定数据目录。

4.  **生成报告**:
    *   在 Playbook 的最后，汇总所有资源的同步结果。
    *   生成一个简明的报告，指出哪些资源同步成功，哪些失败，以及发现的数据不一致情况。此报告可以通过邮件、Webhook 等方式通知管理员。

### **6\. 模式三：手动灾备恢复逻辑详解**

此流程由管理员在灾难发生后，通过 AAP 手动启动一个 Workflow Template 来执行。

#### 流程 0: 灾备切换前置操作 (主站点)

*   **目标**: 在主站点发生故障或计划性切换时，确保数据一致性并准备进行灾备恢复。
*   **实现方式**: 作为 `manual_dr/execute_failover.yml` Playbook 的初始步骤。
*   **角色/任务**:
    1.  **关闭主站点相关虚拟机**:
        *   连接到主 OpenShift 集群 (ocp\_primary)。
        *   识别需要保护的命名空间中的所有虚拟机。
        *   执行 `oc delete vm <vm-name> -n <namespace>` 或 `oc patch vm <vm-name> -p '{"spec":{"running":false}}' --type=merge` 来关闭虚拟机。
    2.  **（可选）设置主存储为只读**:
        *   对于 NFS 场景，连接到主 NFS 服务器。
        *   修改 NFS 导出配置，将相关路径设置为只读，防止进一步写入。
        *   **注意**: 此步骤需根据实际存储类型和自动化能力进行调整。
    3.  **验证数据同步状态**:
        *   虽然 EDA 旨在实时同步，但在灾备切换前，执行最终的数据一致性检查（例如，对于 NFS，可以检查源和目标目录的大小或文件数量，可选基于校验码的验证）。

#### 流程 1-3: 查找并解析备份

*   **角色: oadp_backup_parser**
    1.  **输入**: 由 AAP 调查问卷（Survey）提供要恢复的 `backup_name` (如果为空，则自动查找最新的)。
    2.  在 `localhost` 上执行。
    3.  从 S3 下载指定的 OADP 备份包。
    4.  解压并解析，提取所有 PV 和 PVC 的 JSON 定义，形成 `pv_info_list` 和 `pvc_info_list` 变量。
    5.  **输出**: `pv_info_list` 和 `pvc_info_list` 变量。

#### 流程 4-5: 存储逻辑分发与验证 (NFS 场景)

*   **Playbook 内部逻辑**:
    1.  **输入**: 上一步输出的 `pv_info_list`。
    2.  **逻辑分发**: 使用 `when` 条件或 `include_role` 的 `when` 子句，根据 `item.spec.storageClassName` 来决定执行哪个存储类型的验证逻辑。
    3.  **NFS 验证**: **在灾备站点的 NFS 服务器上 (`delegate_to: dr_nfs_server`)** 执行最终数据同步。根据 `pv_info_list` 中的路径信息，构造 `rsync` 命令，将主 NFS 服务器的数据拉取到灾备 NFS 服务器。这是确保数据最终一致性的关键一步。
        *   **命令示例**: `rsync -av --delete user@primary-nfs:/path/to/data/ /path/to/dr/data/`
        *   在执行实际恢复前，可以先运行 `rsync --dry-run` 进行检查，如果不一致，可以打印警告信息。

#### 流程 6: 在 DR OCP 上部署存储

*   **角色: dr_storage_provisioner**
    1.  **输入**: `pv_info_list` 和 `pvc_info_list`。
    2.  连接到灾备 OCP 集群 (`ocp_dr`)。
    3.  循环遍历 `pv_info_list`，动态生成新的 PV 定义。**关键修改**: 更新 `spec.nfs.server` 为灾备 NFS 服务器 IP，并根据灾备站点的存储布局调整 `spec.nfs.path`。然后将修改后的 PV 定义 `apply` 到灾备集群。
    4.  循环遍历 `pvc_info_list`，并将它们 `apply` 到灾备集群。

#### 7. 在 DR OCP 上恢复应用

*   **角色: oadp_restore_trigger**
    1.  **输入**: `backup_name`。
    2.  连接到灾备 OCP 集群 (`ocp_dr`)。
    3.  动态生成 Restore 对象，`spec.backupName` 设置为输入的 `backup_name`，并且 `excludedResources` 必须包含 `persistentvolumes` 和 `persistentvolumeclaims`。
    4.  `apply` 这个 Restore 对象，并轮询 VM 状态直到成功。

#### 8. 灾备恢复后验证与清理

*   **目标**: 确认灾备恢复成功，并执行必要的清理工作。
*   **实现方式**: 作为 `manual_dr/execute_failover.yml` Playbook 的后续步骤。
*   **角色/任务**:
    1.  **验证虚拟机状态**:
        *   连接到灾备 OpenShift 集群 (`ocp_dr`)。
        *   检查恢复的虚拟机是否处于 `Running` 状态。
        *   可以尝试连接到虚拟机内部，验证应用服务是否正常启动。
    2.  **清理临时文件**:
        *   删除 `oadp_backup_parser` 角色下载和解压的临时备份文件。
    3.  **生成报告**:
        *   记录灾备切换的时间、持续时间、成功或失败状态以及任何关键信息。

### **7\. AAP 平台配置**

1. **EDA Controller 配置**:  
   * 创建一个项目（Project）指向包含 rulebooks/ 目录的 Git 仓库。  
   * 配置一个 Decision Environment（通常使用默认的）。  
   * 创建一个 Rulebook Activation，关联项目和 ocp_dr_events.yml 规则手册，并启动它。  
   * **重要**: 在 Rulebook Activation 中，需要将 Webhook 的 URL 和认证 Token 作为环境变量传递给 `k8s_event_forwarder.py` 的 Deployment。
2. **Workflow 与调度配置**:  
   * **事件驱动 Job Templates**: 创建 Job Template，分别对应 EDA 触发的 `handle_nfs_pv_sync.yml`, `handle_nfs_pv_delete.yml` 等 Playbook。
   * **周期性同步 Job Template**: 创建一个 Job Template，关联 `scheduled/execute_periodic_sync.yml` Playbook。
     * 在此 Job Template 上配置一个 **Schedule**，设置 CRON 表达式（例如 `0 * * * *` 表示每小时执行一次）。
   * **手动恢复 Workflow Template**: 创建一个 "一键灾备切换" Workflow Template，关联 `manual_dr/execute_failover.yml` Playbook，并配置调查问卷以接收 `backup_name`。

通过此番设计，您的灾备方案将提升到一个新的水平，实现了数据同步的自动化和实时性，通过周期性校验保障了最终一致性，同时保留了灾备恢复过程的严谨性和可控性。
