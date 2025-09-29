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
WORK_DIR="/var/lib/genesis/genesis_db"
VENV_PATH="$GC_PATH/.venv"

SYSTEMD_SERVICE_DIR=/etc/systemd/system/

DEV_SDK_PATH="/opt/gcl_sdk"
SDK_DEV_MODE=$([ -d "$DEV_SDK_PATH" ] && echo "true" || echo "false")

PG_VERSION="18"

# Install packages
sudo apt update
sudo apt dist-upgrade -y
sudo apt install -y \
    libev-dev yq watchdog

# Install genesis core
sudo mkdir -p $GC_CFG_DIR
sudo mkdir -p $WORK_DIR
sudo cp "$GC_PATH/etc/genesis_db/genesis_pg_agent.conf" $GC_CFG_DIR/
sudo cp "$GC_PATH/etc/genesis_db/logging.yaml" $GC_CFG_DIR/

mkdir -p "$VENV_PATH"
python3 -m venv "$VENV_PATH"
source "$GC_PATH/.venv/bin/activate"
pip install pip --upgrade
pip install -r "$GC_PATH"/requirements.txt
pip install -e "$GC_PATH"

# In the dev mode the gcl_sdk package is installed from the local machine
if [[ "$SDK_DEV_MODE" == "true" ]]; then
    pip uninstall -y gcl_sdk
    pip install -e "$DEV_SDK_PATH"
fi

# Create links to venv
sudo ln -sf "$VENV_PATH/bin/genesis-universal-agent" "/usr/bin/genesis-db-pg-agent"

deactivate

# Install Systemd service files
sudo cp "$GC_PATH/etc/systemd/genesis-db-pg-agent.service" $SYSTEMD_SERVICE_DIR

# Enable genesis db services
sudo systemctl enable genesis-db-pg-agent


# Patroni

# Install packages
sudo apt-get update
sudo apt-get install postgresql-common -y
sudo YES=1 /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt-get update
sudo apt -y install "postgresql-${PG_VERSION}"
sudo systemctl stop postgresql
sudo systemctl disable postgresql
sudo ln -s /usr/lib/postgresql/$PG_VERSION/bin/* /usr/sbin/

# Setup watchdog
cat <<EOF | sudo tee /etc/udev/rules.d/99-watchdog.rules
KERNEL=="watchdog", OWNER="postgres", GROUP="postgres"
EOF
sudo sh -c 'echo "softdog" >> /etc/modules-load.d/softdog.conf'
sudo sed -i 's/watchdog_module="none"/watchdog_module="softdog"/' /etc/default/watchdog

# Prepare patroni
sudo su postgres <<'EOF'
cd $HOME
mkdir -p patroni
cd patroni
python3 -m venv venv
source venv/bin/activate
pip install "psycopg[binary]" "patroni[raft]>=4.1.0"

mkdir -p data
chmod 750 data
mkdir -p raft
chmod 770 raft
EOF

# Install Systemd service files
sudo cp "$GC_PATH/etc/systemd/genesis-patroni.service" $SYSTEMD_SERVICE_DIR

# Add some usability
sudo ln -sf "/var/lib/postgresql/patroni/venv/bin/patronictl" "/usr/bin/patronictl"
sudo ln -sf "/var/lib/postgresql/patroni/venv/bin/syncobj_admin" "/usr/bin/syncobj_admin"
sudo usermod -a -G postgres ubuntu
# TODO remove wrapper when this script will be executed with ubuntu user
sudo su ubuntu <<'EOF'
mkdir -p ~/.config/patroni
ln -sf "/var/lib/postgresql/patroni/patroni.yml" ~/.config/patroni/patronictl.yaml
ln -sf "/var/lib/postgresql/patroni" ~/patroni
EOF

# Enable genesis db services
sudo systemctl enable \
    genesis-patroni
