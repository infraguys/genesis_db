#!/usr/bin/env bash

#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
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

source /opt/genesis_db/genesis/images/lib_bootstrap.sh

GC_PATH="/opt/genesis_db"

GC_PG_USER="${GC_PG_USER:-genesis_db}"
GC_PG_PASS="${GC_PG_PASS:-pass}"
GC_PG_DB="${GC_PG_DB:-genesis_db}"

PERSISTENT_DISK=$(find_persistent_disk)
prepare_persistent_disk "$(find_persistent_disk)" "$PERSISTENT_MOUNT"

if [[ -n "$PERSISTENT_DISK" ]]; then
    # Migrate logs first, some processes may be left writing to root disk until next reboot
    migrate_to_persistent "/var/log/" "${PERSISTENT_MOUNT}/var/log" "systemd-journald rsyslog"
    migrate_to_persistent_stop_start "/var/lib/postgresql/" "${PERSISTENT_MOUNT}/var/lib/postgresql" "postgresql"
    migrate_to_persistent_stop_start "/var/lib/genesis/" "${PERSISTENT_MOUNT}/var/lib/genesis" "genesis-universal-agent"

    persist_migrate_complete
fi

setup_postgresql_user_and_db "$GC_PG_USER" "$GC_PG_PASS" "$GC_PG_DB"

source "$GC_PATH"/.venv/bin/activate
# Apply main migrations
ra-apply-migration --config-dir "/etc/genesis_db/" --path "$GC_PATH/migrations"
deactivate

# Enable genesis db services
sudo systemctl enable --now \
    genesis-db-gservice \
    genesis-db-user-api \
    genesis-db-status-api \
    genesis-db-orch-api \
    genesis-db-core-agent

echo "Bootstrap completed successfully."
