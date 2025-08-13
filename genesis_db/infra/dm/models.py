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
import uuid as sys_uuid

from gcl_sdk.infra.dm import models as sdk_models
from gcl_sdk.infra import constants as sdk_c
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_db.user_api.dm import models


class PGInstance(models.PGInstance, ua_models.InstanceWithDerivativesMixin):

    __derivative_model_map__ = {
        "node": sdk_models.Node,
        "config": sdk_models.Config,
    }

    @classmethod
    def get_resource_kind(cls) -> str:
        """Return the resource kind."""
        return "pg_instance"

    def get_resource_target_fields(self) -> tp.Collection[str]:
        """Return the collection of target fields.

        Refer to the Resource model for more details about target fields.
        """
        return frozenset(
            (
                "uuid",
                "name",
                "cpu",
                "ram",
                "disk_size",
                "nodes_number",
                "sync_replica_number",
                "version",
                "project_id",
            )
        )

    def get_infra(
        self,
        project_id: sys_uuid.UUID,
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Return the infrastructure objects."""
        infra_objects = []

        node_set = sdk_models.NodeSet(
            uuid=self.uuid,
            name=self.name,
            cores=self.cpu,
            ram=self.ram,
            root_disk_size=self.disk_size,
            image=self.version.image,
            replicas=self.nodes_number,
            project_id=project_id,
            status=sdk_c.NodeStatus.NEW.value,
        )
        infra_objects.append(node_set)

        # TODO: Remove nodes
        # NOTE(akremenetsky): Sets aren't supported yet so create
        # nodes directly. This part will be removed when sets are
        # supported.
        for i in range(self.nodes_number):
            node = sdk_models.Node(
                uuid=sys_uuid.uuid5(self.uuid, f"node-{i}"),
                name=f"{self.name}-node-{i}",
                cores=self.cpu,
                ram=self.ram,
                root_disk_size=self.disk_size,
                image=self.version.image,
                project_id=project_id,
                status=sdk_c.NodeStatus.NEW.value,
            )
            config = sdk_models.Config(
                uuid=sys_uuid.uuid5(self.uuid, f"config-{i}"),
                name=f"{self.name}-config-{i}",
                project_id=project_id,
                status=sdk_c.InstanceStatus.NEW.value,
                target=sdk_models.NodeTarget(
                    node=node.uuid,
                ),
                body=sdk_models.TextBodyConfig(
                    content="",
                ),
                path="/etc/genesis_db/patroni.yaml",
            )
            infra_objects.append(node)
            infra_objects.append(config)

        node_set.nodes = [node.uuid for node in infra_objects[1:]]

        return infra_objects
