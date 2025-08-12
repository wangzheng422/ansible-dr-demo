# k8s_event_forwarder.py

import os
import requests
import time
import json
import threading
from kubernetes import client, config, watch

# 从环境变量中获取EDA Webhook的URL
EDA_WEBHOOK_URL = os.environ.get("EDA_WEBHOOK_URL")
if not EDA_WEBHOOK_URL:
    raise ValueError("环境变量 EDA_WEBHOOK_URL 未设置！")

def send_event_to_eda(payload):
    """将格式化后的事件载荷发送到EDA Webhook"""
    try:
        print(f"发送事件: Kind={payload['kind']}, Type={payload['type']}, Name={payload['resource']['metadata']['name']}")
        requests.post(EDA_WEBHOOK_URL, json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"发送事件到EDA失败: {e}")

def watch_kubernetes_resource(api_call, resource_kind):
    """一个通用的、用于监视指定K8s资源并转发事件的工作函数"""
    while True:
        try:
            print(f"开始监视 {resource_kind} 资源...")
            w = watch.Watch()
            # 使用指定的API调用来启动事件流
            for event in w.stream(api_call):
                # 构造我们自己的JSON载荷
                payload = {
                    "type": event['type'],          # ADDED, MODIFIED, DELETED
                    "kind": resource_kind,
                    "resource": event['object'].to_dict() # 将K8s对象转换为字典
                }
                send_event_to_eda(payload)
        except client.ApiException as e:
            if e.status == 410: # "Gone" - 资源版本太旧，监视中断
                print(f"监视 {resource_kind} 时连接中断 (410 Gone)，立即重连...")
            else:
                print(f"监视 {resource_kind} 时发生API错误: {e}")
                print("将在30秒后重试...")
                time.sleep(30)
        except Exception as e:
            print(f"监视 {resource_kind} 时发生未知错误: {e}")
            print("将在30秒后重试...")
            time.sleep(30)

if __name__ == "__main__":
    # 加载in-cluster配置，让程序在Pod内部自动认证
    print("加载 in-cluster Kubernetes 配置...")
    config.load_incluster_config()
    print("配置加载成功。")

    # 创建API客户端实例
    core_v1_api = client.CoreV1Api()
    snapshot_v1_api = client.CustomObjectsApi()
    
    # 为两种不同的资源创建并启动独立的监视线程
    # 线程1: 监视 PersistentVolumes
    pv_thread = threading.Thread(
        target=watch_kubernetes_resource,
        args=(core_v1_api.list_persistent_volume, "PersistentVolume"),
        daemon=True
    )

    # 线程2: 监视 VolumeSnapshots
    # 注意: VolumeSnapshot是Custom Resource, 使用CustomObjectsApi
    snapshot_thread = threading.Thread(
        target=watch_kubernetes_resource,
        args=(
            lambda: snapshot_v1_api.list_cluster_custom_object(
                group="snapshot.storage.k8s.io",
                version="v1",
                plural="volumesnapshots"
            ),
            "VolumeSnapshot"
        ),
        daemon=True
    )
    
    pv_thread.start()
    snapshot_thread.start()
    
    # 主线程保持运行，以便子线程可以继续工作
    while True:
        time.sleep(60)
        if not pv_thread.is_alive() or not snapshot_thread.is_alive():
            print("错误：一个或多个监视线程已停止！程序将退出。")
            break
