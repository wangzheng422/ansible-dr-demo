# How to Run Ansible Rulebooks from CLI for Testing

This document outlines the steps to run an Ansible Rulebook from the command-line interface (CLI) for testing purposes. This is particularly useful for verifying the logic and actions of your rulebooks before deploying them in a production environment.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Ansible Rulebook**: This is the core component for executing event-driven rules.
*   **Ansible Automation Platform (AAP) Event-Driven Ansible (EDA) Controller** (optional, for `run_job_template` actions): If your rulebook contains `run_job_template` actions, you'll need access to an AAP EDA Controller. For debug-only rulebooks, this is not strictly necessary.
*   **Python and necessary libraries**: Ensure your Python environment is set up correctly and any required Python libraries for your sources (e.g., `sabre1041.eda.k8s` for Kubernetes events) are installed.

## Running a Rulebook

To run a rulebook from the CLI, you use the `ansible-rulebook` command.

### Basic Command Structure

The basic command to run a rulebook is:

```bash
ansible-rulebook --rulebook <path_to_rulebook_file> --verbose
```

### Example: Running `ocp_pv_listener_debug.yml`

Let's use the `ocp_pv_listener_debug.yml` rulebook as an example. This rulebook listens for OpenShift Persistent Volume changes and outputs debug messages.

1.  **Navigate to the project root directory**:
    Ensure you are in the root directory of your Ansible project where the `rulebooks` directory is located. In this case, it's `/Users/zhengwan/Desktop/dev/ansible-dr-demo`.

    ```bash
    cd /Users/zhengwan/Desktop/dev/ansible-dr-demo
    ```

2.  **Execute the rulebook**:
    Run the following command to start the rulebook. The `--verbose` flag provides more detailed output, which is helpful for debugging.

    ```bash
    ansible-rulebook --rulebook rulebooks/ocp_pv_listener_debug.yml --verbose
    ```

### Passing Extra Variables

Some rulebooks, like `ocp_pv_listener_debug.yml`, require external variables to be passed for things like API keys or hostnames. You can pass these using the `--vars` flag, pointing to a file, or with `--extra-vars` for inline key-value pairs.

**Example: Passing `k8s_host` and `k8s_api_key`**

The `ocp_pv_listener_debug.yml` rulebook requires `k8s_host` and `k8s_api_key` to connect to the Kubernetes API.

1.  **Using `--extra-vars`**:

    You can pass the variables directly on the command line. This is useful for a small number of variables.

    ```bash
    ansible-rulebook \
      --rulebook rulebooks/ocp_pv_listener_debug.yml \
      --extra-vars '{"k8s_host": "https://api.your.openshift.cluster:6443", "k8s_api_key": "your_api_key_here"}' \
      --verbose
    ```

    Replace `"https://api.your.openshift.cluster:6443"` and `"your_api_key_here"` with your actual OpenShift API server URL and a valid API token.

2.  **Using a `--vars` file**:

    For a more organized approach, especially with multiple variables, you can define them in a YAML file (e.g., `vars.yml`):

    ```yaml
    # vars.yml
    k8s_host: "https://api.your.openshift.cluster:6443"
    k8s_api_key: "your_api_key_here"
    ```

    Then, run the rulebook with the `--vars` flag:

    ```bash
    ansible-rulebook \
      --rulebook rulebooks/ocp_pv_listener_debug.yml \
      --vars vars.yml \
      --verbose
    ```

    **Explanation of the command:**
    *   `ansible-rulebook`: The command-line tool for running Ansible Rulebooks.
    *   `--rulebook rulebooks/ocp_pv_listener_debug.yml`: Specifies the path to your rulebook file.
    *   `--verbose`: Increases the verbosity of the output, showing more details about events and actions.

### Simulating Events for Testing

For rulebooks that listen to external sources (like Kubernetes events), you might need to simulate events for comprehensive testing without a live environment. This can be done by piping events into the `ansible-rulebook` command.

**Example of simulating a Kubernetes PV ADDED event:**

First, create a JSON file with a sample event. For `ocp_pv_listener_debug.yml`, an event might look like this (save as `pv_added_event.json`):

```json
{
  "type": "ADDED",
  "resource": {
    "apiVersion": "v1",
    "kind": "PersistentVolume",
    "metadata": {
      "name": "test-nfs-pv",
      "namespace": "default"
    },
    "spec": {
      "capacity": {
        "storage": "1Gi"
      },
      "accessModes": [
        "ReadWriteMany"
      ],
      "nfs": {
        "path": "/exports/test",
        "server": "nfs.example.com"
      },
      "persistentVolumeReclaimPolicy": "Retain",
      "storageClassName": "nfs-dynamic",
      "volumeMode": "Filesystem"
    }
  }
}
```

Then, run the rulebook, piping the event JSON into it:

```bash
cat pv_added_event.json | ansible-rulebook --rulebook rulebooks/ocp_pv_listener_debug.yml --verbose
```

This will process the single event and then exit. For continuous listening, you would typically run the rulebook without piping input, allowing it to connect to the actual event source.

## Expected Output

When running `ocp_pv_listener_debug.yml` with a simulated event, you should see output similar to this (depending on the event type):

```
...
DEBUG: NFS PV Created or Modified: test-nfs-pv (Type: ADDED)
...
```

This indicates that the rulebook successfully processed the event and executed the `debug` action.
