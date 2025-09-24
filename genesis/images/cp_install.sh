#!/usr/bin/env bash

# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

set -eu
set -x
set -o pipefail


GC_PATH="/opt/genesis_db"
GC_CFG_DIR=/etc/genesis_db
VENV_PATH="$GC_PATH/.venv"
BOOTSTRAP_PATH="/var/lib/genesis/bootstrap/scripts"

GC_PG_USER="genesis_db"
GC_PG_PASS="pass"
GC_PG_DB="genesis_db"

SYSTEMD_SERVICE_DIR=/etc/systemd/system/

DEV_SDK_PATH="/opt/gcl_sdk"
SDK_DEV_MODE=$([ -d "$DEV_SDK_PATH" ] && echo "true" || echo "false")

# Install packages
sudo apt update
sudo apt dist-upgrade -y
sudo apt install -y \
    postgresql \
    libev-dev

# Default creds for genesis db services
sudo -u postgres psql -c "CREATE ROLE $GC_PG_USER WITH LOGIN PASSWORD '$GC_PG_PASS';"
sudo -u postgres psql -c "CREATE DATABASE $GC_PG_DB OWNER $GC_PG_USER;"

# Install genesis core
sudo mkdir -p $GC_CFG_DIR
sudo cp "$GC_PATH/etc/genesis_db/genesis_db.conf" $GC_CFG_DIR/
sudo cp "$GC_PATH/etc/genesis_db/core_agent.conf" $GC_CFG_DIR/
sudo cp "$GC_PATH/etc/genesis_db/logging.yaml" $GC_CFG_DIR/
sudo cp "$GC_PATH/genesis/images/bootstrap.sh" $BOOTSTRAP_PATH/0100-gc-bootstrap.sh

mkdir -p "$VENV_PATH"
python3 -m venv "$VENV_PATH"
source "$GC_PATH"/.venv/bin/activate
pip install pip --upgrade
pip install -r "$GC_PATH"/requirements.txt
pip install -e "$GC_PATH"

# In the dev mode the gcl_sdk package is installed from the local machine
if [[ "$SDK_DEV_MODE" == "true" ]]; then
    pip uninstall -y gcl_sdk
    pip install -e "$DEV_SDK_PATH"
    # Apply SDK migrations
    ra-apply-migration --config-dir "/etc/genesis_db/" --path "/opt/gcl_sdk/gcl_sdk/migrations"
else
    # Apply SDK migrations
    # TODO: Use a command or apply migration on startup
    ra-apply-migration --config-dir "/etc/genesis_db/" --path "$VENV_PATH/lib/python3.12/site-packages/gcl_sdk/migrations"
fi

# Apply migrations
ra-apply-migration --config-dir "/etc/genesis_db/" --path "$GC_PATH/migrations"
deactivate

# Create links to venv
sudo ln -sf "$VENV_PATH/bin/genesis-db-gservice" "/usr/bin/genesis-db-gservice"
sudo ln -sf "$VENV_PATH/bin/genesis-db-user-api" "/usr/bin/genesis-db-user-api"
sudo ln -sf "$VENV_PATH/bin/genesis-db-status-api" "/usr/bin/genesis-db-status-api"
sudo ln -sf "$VENV_PATH/bin/genesis-db-orch-api" "/usr/bin/genesis-db-orch-api"
sudo ln -sf "$VENV_PATH/bin/genesis-universal-agent-db-back" "/usr/bin/genesis-universal-agent-db-back"

# Install Systemd service files
sudo cp "$GC_PATH/etc/systemd/genesis-db-gservice.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-db-user-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-db-status-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-db-orch-api.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-db-core-agent.service" $SYSTEMD_SERVICE_DIR

# Enable genesis db services
sudo systemctl enable \
    genesis-db-gservice \
    genesis-db-user-api \
    genesis-db-status-api \
    genesis-db-orch-api \
    genesis-db-core-agent
