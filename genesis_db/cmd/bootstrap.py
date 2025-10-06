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

import logging

from gcl_iam.tests.functional import clients as iam_clients
from oslo_config import cfg

from genesis_db.common import permissions

cli_opts = [
    cfg.StrOpt(
        "login",
        default="admin",
        help="Login to IAM",
    ),
    cfg.StrOpt(
        "password",
        default="admin",
        help="Password to IAM",
    ),
    cfg.StrOpt(
        "endpoint",
        default="http://core.local.genesis-core.tech:11010/v1/",
        help="Endpoint to IAM",
    ),
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)


ORGANIZATION_UUID = "265ec810-abb1-470f-80f5-abee759ac818"
ORGANIZATION_NAME = "GenesisDBaaS"
PROJECT_NAME = "genesis_db"


def main():
    # Parse command-line options
    cfg.CONF()

    # Configure logging
    log = logging.getLogger(__name__)

    auth = iam_clients.GenesisCoreAuth(
        username=CONF.login, password=CONF.password
    )
    client = iam_clients.GenesisCoreTestRESTClient(
        endpoint=CONF.endpoint, auth=auth
    )

    org = client.create_or_get_organization(
        ORGANIZATION_UUID, name=ORGANIZATION_NAME
    )
    proj = client.create_or_get_project(org["uuid"], name=PROJECT_NAME)

    perms_by_name = {}
    for perm in permissions.ALL_PERMS:
        perms_by_name[perm] = client.create_or_get_permission(perm)

    for role, perms in permissions.ROLES.items():
        role_obj = client.create_or_get_role(role)
        for perm in perms:
            client.create_or_get_permission_binding(
                perms_by_name[perm]["uuid"],
                role_obj["uuid"],
                project_id=proj["uuid"],
            )


if __name__ == "__main__":
    main()
