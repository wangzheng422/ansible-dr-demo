> [!NOTE]
> work in progress
# ansible-dr-demo

This is ansible repo for ocp-v DR soluition/demo.

There are 3 workflow designed, only `ocp-v-dr-automation/playbooks/scheduled/execute_periodic_sync.yml` working right now.

## config ocp primary and dr

You need service account for both ocp cluster, with pv snapshot priviliedges.

```bash
# Connect your 'oc' client to the REMOTE cluster
oc create serviceaccount eda-event-reader -n default

cat << EOF > $BASE_DIR/data/install/eda-pv-event-reader.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: eda-pv-event-reader
rules:
- apiGroups: [""] # Core API group
  resources: ["persistentvolumes", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "patch"]
- apiGroups: ["snapshot.storage.k8s.io"]
  resources: ["volumesnapshots", "volumesnapshotcontents"]
  verbs: ["get", "list", "watch", "create", "patch"]
EOF

oc apply -f $BASE_DIR/data/install/eda-pv-event-reader.yaml

oc create clusterrolebinding eda-pv-reader-binding \
  --clusterrole=eda-pv-event-reader \
  --serviceaccount=default:eda-event-reader

oc config view --minify -o jsonpath='{.clusters[0].cluster.server}'
# Example Output: https://api.demo-01-rhsys.wzhlab.top:6443

oc config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 --decode
# This will print the full -----BEGIN CERTIFICATE-----... content.

# create token of the sa, and save to variable, expire date is 100 years
SA_TOKEN=`oc create token eda-event-reader --duration=876000h -n default`

echo $SA_TOKEN

```

## test on rhel9/rocky9

```bash
mkdir ~/venv
cd ~/venv
python3 -m venv eda-env

source ~/venv/eda-env/bin/activate

pip install ansible-rulebook ansible-core requests kubernetes

ansible-galaxy collection install sabre1041.eda ansible.eda

ansible-galaxy collection install -r requirements.yml

sudo dnf install -y java-17-openjdk-devel

sudo alternatives --config java

cd ~/git/ansible-dr-demo/ocp-v-dr-automation

```

update `hosts.ini`, and `group_vars/all.yml` based on your env. And run testing

```bash
ansible-playbook -i inventory/hosts.ini \
playbooks/scheduled/execute_periodic_sync.yml \
-e @group_vars/all.yml \
-e "ocp_primary_api_key=eyJhb...................." \
-e "ocp_dr_api_key=eyJhbxxxxxx....................." \
-vvv

```

## build image for eda

```bash

cd ~/git/ansible-dr-demo/ocp-event-forward

podman build -t quay.io/wangzheng422/qimgs:ocp-dr-eda-2025.08.14-v02 -f Dockerfile

podman push quay.io/wangzheng422/qimgs:ocp-dr-eda-2025.08.14-v02

```

## run eda on ocp for testing

```bash

oc new-project eda

cd ~/git/ansible-dr-demo/ocp-event-forward

cat rbac.yaml | oc apply -f -


oc delete deploy/eda-k8s-event-forwarder -n eda

cat deployment.yaml | \
sed "s#quay.io/your-repo/eda-k8s-event-forwarder:latest#quay.io/wangzheng422/qimgs:ocp-dr-eda-2025.08.14-v02#g" | \
sed "s#http://your-eda-webhook-url:port#http://192.168.99.1:5000#g" | \
oc apply -f -





```

## config app

<img src="imgs/README.md/2025-08-12-11-40-26.png" width="1024">
