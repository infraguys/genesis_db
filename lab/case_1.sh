#!/bin/bash

set -ue
set -o pipefail

./automation_stop.sh

yq -iy '.raft = {data_dir: "/var/lib/postgresql/patroni/raft/", self_addr: "10.20.0.21:5019", partner_addrs: ["10.20.0.21:5019", "10.20.0.22:5019", "10.20.0.23:5019"]}' /var/lib/postgresql/patroni/patroni.yml

sudo systemctl restart genesis-patroni

echo "Check if everything is ok with all nodes in cluster?"
