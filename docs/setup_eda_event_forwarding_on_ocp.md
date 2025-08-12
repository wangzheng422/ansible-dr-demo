# 在OpenShift上为Ansible EDA配置Kubernetes事件转发

本文档详细说明了如何部署一个事件转发器（Event Forwarder），以便将OpenShift/Kubernetes集群中的特定资源事件（如`PersistentVolume`和`VolumeSnapshot`的创建、更新、删除）安全地发送到在Ansible Automation Platform (AAP) 2.5上运行的EDA (Event-Driven Ansible) Webhook。

## 工作原理

由于AAP中的EDA Webhook运行在AAP集群内部，它通常无法直接访问OpenShift集群的API来监听事件。为了解决这个问题，我们采用了一个“事件转发器”模式。



1.  **事件转发器 (Event Forwarder)**: 我们在OpenShift集群中部署一个专门的Pod。这个Pod运行一个Python脚本，它使用其关联的Service Account的权限来安全地监听集群API。
2.  **监听资源**: 该脚本持续监视（watch）`PersistentVolume`和`VolumeSnapshot`资源的实时变化。
3.  **格式化与发送**: 当监听到一个事件时，脚本会将其格式化为一个统一的JSON载荷，并通过HTTP POST请求发送到预先配置好的AAP EDA Webhook URL。
4.  **EDA规则触发**: AAP中的EDA `ansible.eda.webhook` source接收到这个JSON数据，然后可以根据其内容触发相应的规则和动作（例如，运行一个Playbook）。

这种方法的优势在于：
*   **安全**: 转发器使用标准的、最小权限的RBAC规则在集群内认证，无需暴露敏感的kubeconfig文件。
*   **解耦**: AAP和OpenShift集群是解耦的。AAP不需要知道如何连接到OCP，只需要暴露一个Webhook端点即可。
*   **高效**: 事件是实时推送的，延迟极低。

## 配置步骤

### 第1步：构建并推送事件转发器镜像

事件转发器是一个Python应用，您需要将其构建成一个容器镜像并推送到一个您的OpenShift集群可以访问的镜像仓库（如Quay.io, Docker Hub, 或您自己的私有仓库）。

项目中的 `ocp-event-forward` 目录包含了所有需要的文件。

1.  **进入目录**:
    ```bash
    cd ocp-event-forward
    ```

2.  **构建镜像**:
    ```bash
    docker build -t quay.io/your-repo/eda-k8s-event-forwarder:latest .
    ```
    *请将 `quay.io/your-repo/eda-k8s-event-forwarder:latest` 替换为您自己的镜像仓库地址。*

3.  **推送镜像**:
    ```bash
    docker push quay.io/your-repo/eda-k8s-event-forwarder:latest
    ```

### 第2步：获取AAP EDA Webhook的URL

在您的AAP项目中，找到或创建一个事件驱动的Ansible规则本，其`source`类型为`ansible.eda.webhook`。当您启动这个规则本时，AAP会为其生成一个唯一的Webhook URL。

这个URL通常遵循以下格式：
`http://<aap-controller-hostname>/api/eda/v1/rules/run/<ruleset-id>/<source-name>`

**关键点**:
*   这个URL必须可以从您的OpenShift集群内部访问。
*   如果AAP和OpenShift在同一个网络中，通常可以直接使用内部服务名和端口。
*   如果它们在不同的网络中，您可能需要通过OpenShift的`Route`或`Ingress`来暴露AAP的Webhook服务。

在我们的例子中，`rulebooks/receive_k8s_events.yml`中定义的端口是`5000`。您需要找到AAP为这个规则本生成的、可从OCP访问的完整URL。

### 第3步：配置并部署转发器到OpenShift

现在，我们将配置并应用`rbac.yaml`和`deployment.yaml`。

1.  **配置RBAC**:
    `ocp-event-forward/rbac.yaml`文件定义了转发器所需的权限。您需要确保`namespace`字段与您打算部署转发器的项目（命名空间）一致。默认是`eda`。

2.  **配置Deployment**:
    编辑 `ocp-event-forward/deployment.yaml` 文件，进行以下两处关键修改：

    ```yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: eda-k8s-event-forwarder
      namespace: eda # <--- 确保这个命名空间正确
    spec:
      replicas: 1
      # ...
      spec:
        serviceAccountName: eda-k8s-watcher-sa
        containers:
        - name: forwarder
          # 1. 修改为您自己的镜像地址
          image: quay.io/your-repo/eda-k8s-event-forwarder:latest 
          env:
          - name: EDA_WEBHOOK_URL
            # 2. 修改为您的AAP EDA Webhook URL
            value: "http://your-aap-eda-webhook-url:5000" 
    ```

3.  **应用配置**:
    在您的OpenShift项目（例如`eda`）中，应用这些配置文件。

    ```bash
    # 登录到您的OpenShift集群
    oc login ...

    # 切换到目标项目
    oc project eda

    # 应用RBAC和Deployment
    oc apply -f ocp-event-forward/rbac.yaml
    oc apply -f ocp-event-forward/deployment.yaml
    ```

### 第4步：验证

1.  **检查转发器Pod**:
    确认转发器的Pod正在运行且没有错误。
    ```bash
    oc get pods -l app=eda-k8s-event-forwarder
    ```
    查看其日志，您应该能看到类似 "开始监视..." 的消息。
    ```bash
    oc logs -f deployment/eda-k8s-event-forwarder
    ```

2.  **触发一个事件**:
    在集群中创建一个PV（或者删除一个现有的PV），来触发一个事件。
    ```bash
    # 示例：创建一个简单的NFS PV
    cat <<EOF | oc apply -f -
    apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: test-pv-for-eda
    spec:
      capacity:
        storage: 1Gi
      accessModes:
        - ReadWriteOnce
      nfs:
        path: /tmp
        server: 127.0.0.1
      storageClassName: manual
    EOF
    ```

3.  **检查日志**:
    *   **转发器日志**: 再次查看转发器Pod的日志，您应该能看到 "发送事件..." 的消息。
    *   **AAP EDA日志**: 在AAP的界面或日志中，检查您的规则本是否收到了事件并触发了相应的`debug`或`run_playbook`动作。

通过以上步骤，您就成功地建立了一条从OpenShift集群到AAP EDA的事件管道，实现了真正的事件驱动自动化。
