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

PERMS_OWNER = [
    "genesis_db.pg_instance.create",
    "genesis_db.pg_instance.read",
    "genesis_db.pg_instance.update",
    "genesis_db.pg_instance.delete",
    "genesis_db.database.create",
    "genesis_db.database.read",
    "genesis_db.database.update",
    "genesis_db.database.delete",
    "genesis_db.user.create",
    "genesis_db.user.read",
    "genesis_db.user.update",
    "genesis_db.user.delete",
    "genesis_db.pg_version.read",
]

ALL_PERMS = set(PERMS_OWNER)

ROLES = {
    "owner": PERMS_OWNER,
}
