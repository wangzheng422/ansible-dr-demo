# ansible-dr-demo

## build aap de image

reference to upstream k8s eda, for aap de image build 
- https://github.com/sabre1041/sabre1041.eda/blob/main/README.md

```bash

dnf install -y python3-pip podman ansible

pip3 install ansible-builder --user

mkdir -p /data/tmp
cd /data/tmp

cat << 'EOF' > eda-de-openshift-aap25.yaml
version: 3

images:
  base_image:
    name: 'registry.redhat.io/ansible-automation-platform-25/de-minimal-rhel8:latest'

dependencies:
  galaxy:
    collections:
      - ansible.eda
      - sabre1041.eda
  python_interpreter:
    package_system: "python311"
  system:
    - pkgconfig [platform:rpm]
    - systemd-devel [platform:rpm]
    - gcc [platform:rpm]
    - python3.11-devel [platform:rpm]

options:
  package_manager_path: /usr/bin/microdnf

additional_build_steps:
  append_final:
  # This is a workaround for the bug: https://issues.redhat.com/browse/AAP-32856
    - ENV PYTHONPATH=$PYTHONPATH:/usr/local/lib/python3.11/site-packages:/usr/local/lib64/python3.11/site-packages
EOF

ansible-builder build -f eda-de-openshift-aap25.yaml --container-runtime podman -v3 --squash all --prune-images -t quay.io/wangzheng422/qimgs:k8s-eda-de-openshift-aap25-2025.08.11

podman push quay.io/wangzheng422/qimgs:k8s-eda-de-openshift-aap25-2025.08.11


```

## test on linux

```bash
mkdir ~/venv
cd ~/venv
python3 -m venv eda-env

source ~/venv/eda-env/bin/activate

pip install ansible-rulebook ansible-core 

ansible-galaxy collection install sabre1041.eda ansible.eda

pip install requests kubernetes

sudo dnf install -y java-17-openjdk-devel

sudo alternatives --config java


ansible-rulebook --rulebook rulebooks/ocp_pv_listener_debug.yml --verbose


```

## config app

<img src="imgs/README.md/2025-08-12-11-40-26.png" width="1024">

