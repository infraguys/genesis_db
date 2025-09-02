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

from gcl_looper.services import basic

from genesis_db.paas.services import builder as paas_builder
from genesis_db.paas.dm import models as paas_models
from genesis_db.infra.services import builder as infra_builder
from genesis_db.infra.dm import models as infra_models

from gcl_sdk.agents.universal.clients.orch import db as orch_db
from gcl_sdk.agents.universal.services import agent as agent_service
from gcl_sdk.agents.universal.services import scheduler as scheduler_service
from gcl_sdk.agents.universal import utils as ua_utils
from gcl_sdk.agents.universal.drivers import core as core_drivers

LOG = logging.getLogger(__name__)


class GeneralService(basic.BasicService):

    def __init__(self, iter_min_period: float = 1, iter_pause: float = 0.1):
        super().__init__(iter_min_period, iter_pause)

        # Infra builder
        builder_infra = infra_builder.CoreInfraBuilder(
            instance_model=infra_models.PGInstance,
            project_id=sys_uuid.UUID("11111112-f41d-40ff-b530-e8f4e70b53ca"),
        )

        # Infra scheduler
        infra_scheduler = scheduler_service.UniversalAgentSchedulerService(
            capabilities=["node", "config"]
        )

        # Infra agent
        orch_client = orch_db.DatabaseOrchClient()
        agent_uuid = ua_utils.system_uuid()

        core_driver = core_drivers.CoreCapabilityDriver(
            username="admin",
            password="admin",
            user_api_base_url="http://10.20.0.2:11010",
            project_id=sys_uuid.UUID("11111112-f41d-40ff-b530-e8f4e70b53ca"),
            node="/v1/nodes/",
            config="/v1/config/configs/",
        )

        caps_drivers = [
            core_driver,
        ]

        facts_drivers = []

        infra_agent = agent_service.UniversalAgentService(
            agent_uuid=agent_uuid,
            orch_client=orch_client,
            caps_drivers=caps_drivers,
            facts_drivers=facts_drivers,
            iter_min_period=iter_min_period,
        )

        # Services
        self._services = [
            builder_infra,
            infra_scheduler,
            infra_agent,
        ]

        # PaaS builders
        for builder in (
            paas_builder.PGUserBuilder,
            paas_builder.PGDatabaseBuilder,
            # paas_builder.PGSUserPrivilegeBuilder,
        ):
            self._services.append(builder())

    def _setup(self):
        LOG.info("Setup all services")
        for service in self._services:
            service._setup()

    def _iteration(self):
        # Iterate all services
        for service in self._services:
            service._loop_iteration()
