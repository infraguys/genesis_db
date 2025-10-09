#!/bin/bash

set -ue
set -o pipefail

sudo systemctl stop genesis-db-pg-agent genesis-universal-agent
