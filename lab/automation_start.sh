#!/bin/bash

set -ue
set -o pipefail

sudo systemctl start genesis-db-pg-agent genesis-universal-agent

sudo systemctl restart genesis-patroni
