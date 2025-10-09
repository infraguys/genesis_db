#!/bin/bash

set -ue
set -o pipefail

sudo tc qdisc del dev enp1s0 root 2>/dev/null || true
sudo tc qdisc add dev enp1s0 root netem delay 1000ms
