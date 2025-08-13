# 运行和调试 `execute_periodic_sync.yml` Ansible Playbook

本文档将指导您如何在命令行环境下运行和调试 `ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml` Ansible Playbook。

## 1. 前提条件

在运行此Playbook之前，请确保您的系统满足以下条件：

*   **Ansible**: 确保已安装Ansible。推荐使用最新稳定版本。
    ```bash
    pip install ansible
    ```
*   **OpenShift/Kubernetes Python客户端库**: Playbook使用 `kubernetes.core` 集合，这需要安装相应的Python库。
    ```bash
    pip install openshift kubernetes
    ```
*   **Ansible `kubernetes.core` 集合**: 安装Ansible Kubernetes集合。
    ```bash
    ansible-galaxy collection install kubernetes.core
    ```
*   **`oc` CLI工具**: 确保您已安装并配置了OpenShift命令行工具 (`oc`)，并且可以访问您的Primary OCP集群。Playbook会委托任务到Primary OCP集群。
    ```bash
    # 验证oc工具是否可用
    oc version
    # 登录到Primary OCP集群
    oc login --token=<your_token> --server=<your_primary_ocp_api_url>
    ```
*   **Python**: 确保您的系统上安装了Python 3。

## 2. Ansible 清单 (Inventory) 与变量文件 (`group_vars`/`host_vars`) 的区别

在Ansible中，**清单 (Inventory)** 和 **变量文件** 是两个核心概念，它们共同定义了Ansible管理的目标主机以及这些主机相关的配置数据。

### 2.1. 清单 (Inventory)

**清单文件** (例如 `ocp-v-dr-automation/inventory/hosts.ini`) 的主要作用是定义Ansible要管理的主机列表，并将这些主机组织成不同的组。它告诉Ansible“在哪里”运行任务。

*   **作用**:
    *   **主机定义**: 列出所有目标服务器的IP地址或主机名。
    *   **主机分组**: 将相关的主机组织到逻辑组中（例如 `[ocp_primary]`, `[ocp_dr]`, `[nfs_servers]`）。这使得您可以对特定组的主机运行Playbook，而不是对所有主机。
    *   **连接信息**: 可以包含连接到这些主机的特定信息，例如SSH用户、端口、私钥路径等。

*   **示例 (`ocp-v-dr-automation/inventory/hosts.ini`)**:
    ```ini
    [aap_controller]
    aap.example.com

    [ocp_primary]
    primary-cluster.example.com

    [ocp_dr]
    dr-cluster.example.com

    [nfs_servers]
    primary-nfs.example.com
    dr-nfs.example.com
    ```
    在这个Playbook中，`hosts: localhost` 表示Playbook本身在本地运行，但其中的任务（例如 `kubernetes.core.k8s_info`）通过 `delegate_to` 委托给清单中定义的主机（例如 `ocp_primary_cluster_name` 所指向的主机）。

### 2.2. 变量文件 (`group_vars`/`host_vars`)

**变量文件** (例如 `ocp-v-dr-automation/group_vars/all.yml` 或 `host_vars/<hostname>.yml`) 的主要作用是存储与主机或主机组相关的变量。它告诉Ansible“如何”配置这些主机。

*   **作用**:
    *   **配置数据**: 存储应用程序配置、路径、端口、凭据等数据。
    *   **环境特定值**: 为不同的环境（开发、测试、生产）或不同的主机组定义不同的变量值。
    *   **模块参数**: 为Ansible模块提供参数值，使Playbook更具通用性。

*   **类型**:
    *   **`group_vars/<group_name>.yml`**: 适用于特定主机组的所有主机。例如，`group_vars/ocp_primary.yml` 中的变量将应用于 `[ocp_primary]` 组中的所有主机。
    *   **`group_vars/all.yml`**: 适用于清单中所有主机。这是定义全局变量的常用位置。
    *   **`host_vars/<hostname>.yml`**: 适用于单个特定主机。

*   **示例 (`ocp-v-dr-automation/group_vars/all.yml`)**:
    ```yaml
    # ocp-v-dr-automation/group_vars/all.yml
    # OADP Backup Configuration
    oadp_s3_bucket: "ocp"
    oadp_s3_region: "us-east-1"
    oadp_s3_endpoint: "http://192.168.99.1:9000"
    # These should be stored in AAP credential store
    oadp_s3_access_key: "rustfsadmin"
    oadp_s3_secret_key: "rustfsadmin"

    # NFS Configuration
    primary_nfs_server: "192.168.99.1"
    dr_nfs_server: "192.168.99.1"
    primary_nfs_base_path: "/srv/nfs/openshift-01"
    dr_nfs_base_path: "/srv/nfs/openshift-02"

    # DR Workflow Configuration
    default_backup_name: "" # Empty means find the latest
    ```
    在这个Playbook中，`ocp_primary_cluster_name` 变量是必需的，因为它用于 `delegate_to`。虽然它没有在当前的 `group_vars/all.yml` 中，但通常会在这里或通过命令行定义。

**关于 `group_vars/all.yml` 的自动引用**:
Ansible 会自动加载 `group_vars/all.yml` 文件中定义的所有变量，并使其对清单中的所有主机可用。您无需在 `ansible-playbook` 命令中显式引用它。这意味着，只要变量在 `group_vars/all.yml` 中定义，Playbook 就可以直接使用它们。

### 2.3. 总结

*   **Inventory (清单)**: 定义 **“在哪里”** 运行Ansible任务（主机和主机组）。
*   **Variable Files (变量文件)**: 定义 **“如何”** 运行Ansible任务（配置数据和参数）。

它们是Ansible项目不可或缺的组成部分，共同提供了灵活性和可重用性。

## 3. 运行Playbook

使用 `ansible-playbook` 命令运行脚本。请确保您在 `ansible-dr-demo` 目录下执行此命令。

```bash
ansible-playbook -i ocp-v-dr-automation/inventory/hosts.ini \
  ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml \
  -e "ocp_primary_cluster_name=primary-cluster.example.com"
```

**解释**:
*   `-i ocp-v-dr-automation/inventory/hosts.ini`: 指定Ansible清单文件。
*   `ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml`: 指定要运行的Playbook文件。
*   `-e "ocp_primary_cluster_name=primary-cluster.example.com"`: 通过命令行传递 `ocp_primary_cluster_name` 变量。请根据您的实际Primary OCP集群主机名进行替换。

### 3.1. 在启动时覆盖变量

当您需要临时更改在变量文件（如 `group_vars/all.yml`）中定义的变量时，您可以在运行 `ansible-playbook` 命令时通过 `-e` 或 `--extra-vars` 参数来传递新值。通过命令行传递的变量具有较高的优先级，会覆盖清单变量文件中的同名变量。

这对于测试、针对不同环境进行微调或动态传递配置非常有用，而无需修改核心变量文件。

**示例：覆盖 `group_vars` 中的变量**

假设在 `ocp-v-dr-automation/group_vars/all.yml` 文件中定义了 `primary_nfs_server`：

```yaml
# ocp-v-dr-automation/group_vars/all.yml
...
primary_nfs_server: "192.168.99.1"
...
```

如果您希望在本次运行中使用一个不同的NFS服务器地址（例如 `"192.168.100.5"`），您可以在命令行中这样操作：

```bash
ansible-playbook -i ocp-v-dr-automation/inventory/hosts.ini \
  ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml \
  -e "ocp_primary_cluster_name=primary-cluster.example.com" \
  -e "primary_nfs_server=192.168.100.5"
```

在这个命令中，`-e "primary_nfs_server=192.168.100.5"` 将会覆盖文件中 `primary_nfs_server` 的默认值。Ansible在执行Playbook时会使用您在命令行中提供的值。您可以为任何在变量文件中定义的变量使用此方法。

## 4. 调试Playbook

Ansible提供了多种调试选项：

*   **详细输出 (`-v`, `-vv`, `-vvv`, `-vvvv`)**: 增加详细程度以查看更多执行细节。
    *   `-v`: 少量详细信息。
    *   `-vv`: 中等详细信息。
    *   `-vvv`: 更多详细信息，包括模块参数。
    *   `-vvvv`: 调试级别，显示连接和传输信息。
    ```bash
    ansible-playbook -i ocp-v-dr-automation/inventory/hosts.ini \
      ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml \
      -e "ocp_primary_cluster_name=primary-cluster.example.com" -vvv
    ```

*   **检查模式 (`--check`)**: 在不实际执行任何更改的情况下运行Playbook。这对于验证语法和逻辑非常有用。
    ```bash
    ansible-playbook -i ocp-v-dr-automation/inventory/hosts.ini \
      ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml \
      -e "ocp_primary_cluster_name=primary-cluster.example.com" --check
    ```

*   **差异模式 (`--diff`)**: 显示Playbook将要进行的更改的差异。这在与 `--check` 结合使用时特别有用。
    ```bash
    ansible-playbook -i ocp-v-dr-automation/inventory/hosts.ini \
      ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml \
      -e "ocp_primary_cluster_name=primary-cluster.example.com" --diff
    ```

*   **启动Playbook从特定任务开始 (`--start-at-task`)**: 如果Playbook在某个任务失败，您可以在修复问题后从该任务重新开始，而不是从头运行整个Playbook。
    ```bash
    ansible-playbook -i ocp-v-dr-automation/inventory/hosts.ini \
      ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml \
      -e "ocp_primary_cluster_name=primary-cluster.example.com" \
      --start-at-task "Loop through each PV and sync"
    ```
    **注意**: 任务名称必须与Playbook中定义的 `name` 完全匹配。

*   **使用 `debug` 模块**: 在Playbook中添加 `ansible.builtin.debug` 任务来打印变量的值或任务的输出。
    例如，在 `execute_periodic_sync.yml` 中，已经有一个 `debug` 任务来显示同步报告。您可以在任何任务之后添加类似的 `debug` 任务来检查 `nfs_pvs` 或 `snapshots` 变量的内容。
    ```yaml
    - name: "Get all NFS PVs from Primary OCP"
      kubernetes.core.k8s_info:
        api_version: v1
        kind: PersistentVolume
        label_selectors:
          - storageClassName=nfs-dynamic
      register: nfs_pvs
      delegate_to: "{{ ocp_primary_cluster_name }}"

    - name: "Debug NFS PVs" # 新增的调试任务
      ansible.builtin.debug:
        var: nfs_pvs
    ```

*   **限制主机 (`--limit`)**: 如果您的清单中有多个主机，您可以使用 `--limit` 选项将Playbook的执行限制到特定主机或组。虽然此Playbook `hosts: localhost`，但如果内部角色委托给其他主机，这仍然有用。
    ```bash
    ansible-playbook -i ocp-v-dr-automation/inventory/hosts.ini \
      ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml \
      -e "ocp_primary_cluster_name=primary-cluster.example.com" \
      --limit primary-cluster.example.com
    ```

通过结合使用这些工具和技术，您可以有效地运行和调试 `execute_periodic_sync.yml` Ansible Playbook。

```bash

cd ~/git/ansible-dr-demo/ocp-v-dr-automation

ansible-playbook -i inventory/hosts.ini \
  playbooks/scheduled/execute_periodic_sync.yml \
  -e "ocp_primary_cluster_name=primary-cluster.example.com" -vvv


cd ~/git/ansible-dr-demo/ocp-v-dr-automation

ansible-playbook -i inventory/hosts.ini \
playbooks/scheduled/execute_periodic_sync.yml \
-e @group_vars/all.yml \
-e "ocp_primary_cluster_name=primary-cluster.example.com" -vvv



```