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
import uuid as sys_uuid
import typing as tp
import uuid

from gcl_sdk.paas.services import builder
from gcl_sdk.infra import constants as sdk_c
from gcl_sdk.infra.dm import models as sdk_models
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_db.paas.dm import models

LOG = logging.getLogger(__name__)
NODE_KIND = sdk_models.Node.get_resource_kind()
CONFIG_KIND = sdk_models.Config.get_resource_kind()
AGENT_UUID5_NAME = "dbaas"


class PaaSBuilder(builder.PaaSBuilder):

    @classmethod
    def agent_uuid_by_node(cls, node_uuid: sys_uuid.UUID) -> sys_uuid.UUID:
        return sys_uuid.uuid5(node_uuid, AGENT_UUID5_NAME)

    def schedule_paas_objects(
        self,
        instance: ua_models.InstanceWithDerivativesMixin,
        paas_objects: tp.Collection[ua_models.TargetResourceKindAwareMixin],
    ) -> dict[
        sys_uuid.UUID, tp.Collection[ua_models.TargetResourceKindAwareMixin]
    ]:
        """Schedule the PaaS objects.

        The method schedules the PaaS objects. The result is a dictionary
        where the key is a UUID of a agent and the value is a list of PaaS
        objects that should be scheduled on this agent.
        """

        scheduled = {}
        for entity in paas_objects:
            # We hardcode entity's uuid the same as agents's uuid
            scheduled[entity.uuid] = [entity]
        return scheduled


class PGInstanceBuilder(PaaSBuilder):

    def __init__(
        self,
        instance_model: tp.Type[models.PGInstance] = models.PGInstance,
    ):
        super().__init__(instance_model)

    def _get_users(self, instance):
        return {
            u.name: {
                # Don't give actual password to dataplane, just hash it
                "pw_hash": u.password_hash,
            }
            for u in instance.get_users()
        }

    def _get_databases(self, instance):
        return {
            d.name: {"owner": d.owner.name} for d in instance.get_databases()
        }

    def create_paas_objects(
        self, instance: models.PGInstance
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Create a list of PaaS objects.

        The method returns a list of PaaS objects that are required
        for the instance.
        """

        return self.actualize_paas_objects(
            instance, builder.PaaSCollection(paas_objects=tuple())
        )

    def actualize_paas_objects(
        self,
        instance: models.PGInstance,
        paas_collection: builder.PaaSCollection,
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Basic update, all derivatives are non-unique"""

        actual_resources = []

        users = self._get_users(instance)

        databases = self._get_databases(instance)

        nodeset = instance.get_actual_nodeset()
        nodes_by_idx = list(nodeset.nodes.keys())

        # Support only PGInstanceNode
        for res in paas_collection.targets():
            if not isinstance(res, models.PGInstanceNode):
                LOG.warning(
                    "PGInstanceBuilder doesn't support %s model type",
                    res.__class__.__name__,
                )
            for k, v in dict(
                name=instance.name,
                instance=instance,
                nodes_number=instance.nodes_number,
                sync_replica_number=instance.sync_replica_number,
                users=users,
                databases=databases,
            ).items():
                setattr(res, k, v)
            actual_resources.append(res)

        diff_num = instance.nodes_number - len(actual_resources)

        # Shrink - just remove N nodes from the end
        if diff_num < 0:
            for _ in range(-diff_num):
                del actual_resources[-1]
        # Add new nodes
        elif diff_num > 0:
            start_num = len(actual_resources)
            for i in range(start_num + 1, start_num + diff_num + 1):
                actual_resources.append(
                    models.PGInstanceNode(
                        uuid=PaaSBuilder.agent_uuid_by_node(
                            uuid.UUID(nodes_by_idx[i - 1])
                        ),
                        name=instance.name,
                        instance=instance,
                        nodes_number=instance.nodes_number,
                        sync_replica_number=instance.sync_replica_number,
                        users=users,
                        databases=databases,
                    )
                )

        return actual_resources
