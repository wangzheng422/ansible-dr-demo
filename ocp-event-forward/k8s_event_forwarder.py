# k8s_event_forwarder.py

import os
import requests
import time
import json
import threading
from kubernetes import client, config, watch

# Get EDA Webhook URL from environment variable
EDA_WEBHOOK_URL = os.environ.get("EDA_WEBHOOK_URL")
if not EDA_WEBHOOK_URL:
    raise ValueError("Environment variable EDA_WEBHOOK_URL is not set!")

def send_event_to_eda(payload):
    """Sends the formatted event payload to the EDA Webhook."""
    try:
        print(f"Sending event: Kind={payload['kind']}, Type={payload['type']}, Name={payload['resource']['metadata']['name']}")
        # Use json.dumps with default=str to handle datetime objects
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(payload, default=str)
        requests.post(EDA_WEBHOOK_URL, data=data, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Failed to send event to EDA: {e}")

def watch_kubernetes_resource(api_call, resource_kind):
    """A generic worker function to watch a specified K8s resource and forward events."""
    while True:
        try:
            print(f"Starting to watch {resource_kind} resources...")
            w = watch.Watch()
            # Use the specified API call to start the event stream
            for event in w.stream(api_call):
                # Construct our own JSON payload
                payload = {
                    "type": event['type'],          # ADDED, MODIFIED, DELETED
                    "kind": resource_kind,
                    "resource": event['object'].to_dict() # Convert K8s object to a dictionary
                }
                send_event_to_eda(payload)
        except client.ApiException as e:
            if e.status == 410: # "Gone" - The resource version is too old, watch is interrupted
                print(f"Watch connection closed for {resource_kind} (410 Gone), reconnecting immediately...")
            else:
                print(f"API error while watching {resource_kind}: {e}")
                print("Retrying in 30 seconds...")
                time.sleep(30)
        except Exception as e:
            print(f"Unknown error while watching {resource_kind}: {e}")
            print("Retrying in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    # Load in-cluster configuration for automatic authentication within a Pod
    print("Loading in-cluster Kubernetes configuration...")
    config.load_incluster_config()
    print("Configuration loaded successfully.")

    # Create API client instances
    core_v1_api = client.CoreV1Api()
    snapshot_v1_api = client.CustomObjectsApi()
    
    # Create and start separate watch threads for multiple resources
    # Thread 1: Watch PersistentVolumes
    pv_thread = threading.Thread(
        target=watch_kubernetes_resource,
        args=(core_v1_api.list_persistent_volume, "PersistentVolume"),
        daemon=True
    )

    # Thread 2: Watch PersistentVolumeClaims
    pvc_thread = threading.Thread(
        target=watch_kubernetes_resource,
        args=(core_v1_api.list_persistent_volume_claim_for_all_namespaces, "PersistentVolumeClaim"),
        daemon=True
    )

    # Thread 3: Watch VolumeSnapshots
    snapshot_thread = threading.Thread(
        target=watch_kubernetes_resource,
        args=(
            lambda **kwargs: snapshot_v1_api.list_cluster_custom_object(
                group="snapshot.storage.k8s.io",
                version="v1",
                plural="volumesnapshots",
                **kwargs
            ),
            "VolumeSnapshot"
        ),
        daemon=True
    )

    # Thread 4: Watch VolumeSnapshotContents
    snapshotcontent_thread = threading.Thread(
        target=watch_kubernetes_resource,
        args=(
            lambda **kwargs: snapshot_v1_api.list_cluster_custom_object(
                group="snapshot.storage.k8s.io",
                version="v1",
                plural="volumesnapshotcontents",
                **kwargs
            ),
            "VolumeSnapshotContent"
        ),
        daemon=True
    )
    
    pv_thread.start()
    pvc_thread.start()
    snapshot_thread.start()
    snapshotcontent_thread.start()
    
    # Keep the main thread alive so that the daemon threads can continue to work
    while True:
        time.sleep(60)
        if not all([pv_thread.is_alive(), pvc_thread.is_alive(), snapshot_thread.is_alive(), snapshotcontent_thread.is_alive()]):
            print("Error: One or more watch threads have stopped! The program will exit.")
            break
