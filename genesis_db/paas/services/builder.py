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
from gcl_sdk.infra.dm import models as sdk_models
from gcl_sdk.agents.universal.dm import models as ua_models

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

    # def post_create_instance_resource(
    #     self,
    #     instance: (
    #         ua_models.InstanceMixin | ua_models.InstanceWithDerivativesMixin
    #     ),
    #     resource: ua_models.TargetResource,
    #     derivatives: tp.Collection[ua_models.TargetResource] = tuple(),
    # ) -> None:
    #     import pdb; pdb.set_trace()
    #     super().post_create_instance_resource(instance, resource, derivatives)

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

        nodes = instance.get_infra()[1:]
        scheduled = {}
        for node, node_entity in zip(nodes, paas_objects):
            agent_uuid = self.agent_uuid_by_node(node.uuid)
            scheduled[agent_uuid] = [node_entity]
        return scheduled

    def actualize_paas_objects_source_data_plane(
        self,
        instance: ua_models.InstanceWithDerivativesMixin,
        paas_collection: builder.PaaSCollection,
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Actualize the PaaS objects. Changes from the data plane.

        The method is called when the instance is outdated. For example,
        the instance `Database` has derivative `PGDatabase`. Single `Database`
        may have multiple `PGDatabase` derivatives. If any of the derivatives
        is outdated, this method is called to reactualize this PaaS objects.

        Args:
            instance: The instance to actualize.
            paas_objects: The actual PaaS objects.
        """
        return paas_collection.targets()

    def actualize_paas_objects_source_master(
        self,
        instance: ua_models.InstanceWithDerivativesMixin,
        master_instance: ua_models.InstanceWithDerivativesMixin,
        paas_collection: builder.PaaSCollection,
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Actualize the PaaS objects. Changes from the master instance.

        The method is called when the instance is outdated from master
        instance point of view. For example, the instance `Database` is linked to the
        `NodeSet` instance. If the `NodeSet` is outdated, this method is called
        to reactualize the `Database` instance.

        Args:
            instance: The instance to actualize.
            master_instance: The master instance.
            paas_collection: The actual PaaS objects.
        """
        return paas_collection.targets()


class PGUserBuilder(PaaSBuilder):

    def __init__(
        self,
        instance_model: tp.Type[models.PGUser] = models.PGUser,
    ):
        super().__init__(instance_model)

    def create_paas_objects(
        self, instance: models.PGUser
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Create a list of PaaS objects.

        The method returns a list of PaaS objects that are required
        for the instance.
        """
        # Get the infrastructure for the current PG instance
        nodes = instance.get_infra()[1:]

        # Don't give actual password to dataplane, just hash it
        password_hash = passwd.scram_sha_256(instance.password)

        # Create the same derivatives database objects as nodes in the node set
        return tuple(
            models.PGUserNode(
                uuid=sys_uuid.uuid5(instance.uuid, str(node.uuid)),
                name=instance.name,
                instance=instance,
                password_hash=password_hash,
            )
            for node in nodes
        )


class PGDatabaseBuilder(PaaSBuilder):

    def __init__(
        self,
        instance_model: tp.Type[models.PGDatabase] = models.PGDatabase,
    ):
        super().__init__(instance_model)

    def create_paas_objects(
        self, instance: models.PGDatabase
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Create a list of PaaS objects.

        The method returns a list of PaaS objects that are required
        for the instance.
        """
        # Get the infrastructure for the current PG instance
        nodes = instance.get_infra()[1:]

        # Create the same derivatives database objects as nodes in the node set
        return tuple(
            models.PGDatabaseNode(
                uuid=sys_uuid.uuid5(instance.uuid, str(node.uuid)),
                name=instance.name,
                instance=instance,
                owner=instance.owner.name,
            )
            for node in nodes
        )


# class PGSUserPrivilegeBuilder(builder.PaaSBuilder):

#     def __init__(
#         self,
#         instance_model: tp.Type[
#             models.PGUserPrivilege
#         ] = models.PGUserPrivilege,
#     ):
#         super().__init__(instance_model)

#     def create_paas_objects(
#         self, instance: models.PGDatabase
#     ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
#         """Create a list of PaaS objects.

#         The method returns a list of PaaS objects that are required
#         for the instance.
#         """
#         # Get the infrastructure for the current PG instance
#         nodes = instance.get_infra()[1:]

#         # Create the same derivatives database objects as nodes in the node set
#         return tuple(
#             models.PGUserPrivilegeNode(
#                 uuid=sys_uuid.uuid5(instance.uuid, str(node.uuid)),
#                 database=instance.database.name,
#                 username=instance.name,
#                 instance=instance,
#                 kind=instance.kind.KIND,
#                 kind_name=instance.kind.name,
#                 privileges=instance.kind.privileges,
#             )
#             for node in nodes
#         )
