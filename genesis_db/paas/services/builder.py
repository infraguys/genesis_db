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

from gcl_sdk.paas.services import builder
from gcl_sdk.infra import constants as sdk_c
from gcl_sdk.infra.dm import models as sdk_models
from gcl_sdk.agents.universal.dm import models as ua_models
from gcl_sdk.agents.universal import utils

from genesis_db.common.pg_auth import passwd
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

        nodes = instance.get_infra()
        scheduled = {}
        for node, node_entity in zip(nodes, paas_objects):
            agent_uuid = self.agent_uuid_by_node(node.uuid)
            scheduled[agent_uuid] = [node_entity]
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
                "pw_hash": passwd.scram_sha_256(u.password),
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

        # Get the infrastructure for the current PG instance
        nodes = instance.get_infra()

        users = self._get_users(instance)

        databases = self._get_databases(instance)

        instance.status = sdk_c.InstanceStatus.IN_PROGRESS.value

        # Create the same derivatives database objects as nodes in the node set
        return tuple(
            models.PGInstanceNode(
                uuid=sys_uuid.uuid5(instance.uuid, str(node.uuid)),
                name=instance.name,
                instance=instance,
                sync_replica_number=instance.sync_replica_number,
                users=users,
                databases=databases,
            )
            for node in nodes
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
                sync_replica_number=instance.sync_replica_number,
                users=users,
                databases=databases,
            ).items():
                setattr(res, k, v)
            actual_resources.append(res)

        if all(
            actual_res  # may not exist yet
            and actual_res.status == sdk_c.InstanceStatus.ACTIVE.value
            and len(actual_res.users) == len(users)
            and len(actual_res.databases) == len(databases)
            for actual_res in paas_collection.actuals()
        ):
            instance.status = sdk_c.InstanceStatus.ACTIVE.value
        else:
            instance.status = sdk_c.InstanceStatus.IN_PROGRESS.value

        return actual_resources
