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

import typing as tp
import logging

from restalchemy.dm import types as ra_types
from restalchemy.dm import models as ra_models
from restalchemy.dm import properties
from gcl_sdk.infra.dm import models as sdk_models
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_db.user_api.dm import models


LOG = logging.getLogger(__name__)


class PGDatabaseNode(
    ra_models.ModelWithUUID,
    ra_models.ModelWithNameDesc,
    ra_models.ModelWithTimestamp,
    ua_models.TargetResourceKindAwareMixin,
):
    # TODO(akremenetsky): We already have name in the parent model
    name = properties.property(ra_types.String(min_length=1, max_length=255))

    @classmethod
    def get_resource_kind(cls) -> str:
        """Return the resource kind."""
        return "pg_database_node"

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            (
                "uuid",
                "name",
            )
        )


class PGDatabase(
    models.PGDatabase,
    ua_models.InstanceWithDerivativesMixin,
):

    __master_model__ = sdk_models.NodeSet
    __derivative_model_map__ = {
        "pg_database_node": PGDatabaseNode,
    }

    @classmethod
    def get_resource_kind(cls) -> str:
        """Return the resource kind."""
        return "pg_database"

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            (
                "uuid",
                "name",
                "instance",
                "project_id",
            )
        )

    def get_infra(self) -> tp.Collection[sdk_models.NodeSet | sdk_models.Node]:
        # TODO(akremenetsky): Temporarily solution since we don't have sets
        # support yet

        node_set = sdk_models.NodeSet.get_one_from_resource_storage(
            self.instance.uuid
        )

        # Need to filter nodes by node_set.uuid
        nodes = sdk_models.Node.get_all_from_resource_storage()

        return [node_set] + list(nodes)
