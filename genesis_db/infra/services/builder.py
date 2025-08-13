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

from gcl_sdk.infra.services import builder
from gcl_sdk.infra import constants as sdk_c
from gcl_sdk.infra.dm import models as sdk_models
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_db.infra.dm import models

LOG = logging.getLogger(__name__)
NODE_KIND = sdk_models.Node.get_resource_kind()
CONFIG_KIND = sdk_models.Config.get_resource_kind()


class CoreInfraBuilder(builder.CoreInfraBuilder):

    def __init__(
        self,
        instance_model: tp.Type[models.PGInstance],
        project_id: sys_uuid.UUID,
    ):
        super().__init__(instance_model)
        self._project_id = project_id

    def create_infra(
        self, instance: models.PGInstance
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Create a list of infrastructure objects.

        The method returns a list of infrastructure objects that are required
        for the instance. For example, nodes, sets, configs, etc.
        """
        return instance.get_infra(self._project_id)

    def actualize_infra(
        self,
        instance: models.PGInstance,
        infra: builder.InfraCollection,
    ) -> tp.Collection[ua_models.TargetResourceKindAwareMixin]:
        """Actualize the infrastructure objects.

        The method is called when the instance is outdated. For example,
        the instance `Config` has derivative `Render`. Single `Config` may
        have multiple `Render` derivatives. If any of the derivatives is
        outdated, this method is called to reactualize this infrastructure.

        Args:
            instance: The instance to actualize.
            infra: The infrastructure objects.
        """
        nodes = []
        configs = []

        for _, actual in infra.infra_objects:
            if actual.get_resource_kind() == NODE_KIND:
                nodes.append(actual)
            elif actual.get_resource_kind() == CONFIG_KIND:
                configs.append(actual)

        node_ips = [node.default_network.get("ipv4", "") for node in nodes]
        content = "\n".join(node_ips)

        # Update config content
        for target, _ in infra.infra_objects:
            if target.get_resource_kind() != CONFIG_KIND:
                continue
            if target.body.content != content:
                target.body.content = content

        if all(
            config.status == sdk_c.InstanceStatus.ACTIVE.value
            for config in configs
        ):
            instance.status = sdk_c.InstanceStatus.ACTIVE.value
        else:
            instance.status = sdk_c.InstanceStatus.IN_PROGRESS.value

        # Return the target resources
        return infra.targets()
