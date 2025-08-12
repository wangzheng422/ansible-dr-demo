### 项目名称：OCP-V 事件驱动灾备自动化项目

### **1\. 项目目标与双模架构**

目标：  
本项目旨在构建一个双模式、高度自动化的 OCP-V 灾备解决方案。它结合了 Ansible Automation Platform (AAP) EDA 的实时事件处理能力和传统的 AAP Workflow 的手动恢复能力，以实现数据近实时同步和一键式灾备切换。  
**双模架构：**

1. **模式一：事件驱动的实时数据复制 (Event-Driven Replication)**  
   * **核心**：AAP Event-Driven Ansible (EDA) Controller。  
   * **目标**：通过监听主 OpenShift 集群的 PV（PersistentVolume）事件，自动、实时地将底层存储数据同步到灾备站点。这取代了原方案中定时的、批量的同步任务。  
2. **模式二：手动触发的灾备恢复 (Manual Failover)**  
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

**模式二: 手动灾备恢复 (Manual Failover)**
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
│   └── oadp_restore_trigger/     # 角色: (DR用) 执行OADP恢复
└── playbooks/
    ├── event_driven/
    │   ├── handle_nfs_pv_sync.yml    # Playbook: (EDA用) 调用nfs_sync_on_event
    │   ├── handle_nfs_pv_delete.yml  # Playbook: (EDA用) 调用nfs_delete_on_event
    │   ├── handle_snapshot_sync.yml  # Playbook: (EDA用) 调用snapshot_sync_on_event
    │   └── handle_snapshot_delete.yml# Playbook: (EDA用) 调用snapshot_delete_on_event
    └── manual_dr/
        └── execute_failover.yml      # Playbook: (DR用) 执行完整的灾备切换
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

### **5\. 模式二：手动灾备恢复逻辑详解**

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

### **6\. AAP 平台配置**

1. **EDA Controller 配置**:  
   * 创建一个项目（Project）指向包含 rulebooks/ 目录的 Git 仓库。  
   * 配置一个 Decision Environment（通常使用默认的）。  
   * 创建一个 Rulebook Activation，关联项目和 ocp_dr_events.yml 规则手册，并启动它。  
   * **重要**: 在 Rulebook Activation 中，需要将 Webhook 的 URL 和认证 Token 作为环境变量传递给 `k8s_event_forwarder.py` 的 Deployment。
2. **Workflow 配置**:  
   * 创建两个 Job Template，分别对应 EDA 触发的 handle_nfs_pv_sync.yml 和 handle_nfs_pv_delete.yml。  
   * 创建一个 "一键灾备切换" Workflow Template，关联 manual_dr/execute_failover.yml Playbook，并配置调查问卷以接收 backup_name。

通过此番设计，您的灾备方案将提升到一个新的水平，实现了数据同步的自动化和实时性，同时保留了灾备恢复过程的严谨性和可控性。
