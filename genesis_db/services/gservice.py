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
from __future__ import annotations

import typing as tp

import os
import logging
import uuid as sys_uuid

from gcl_looper.services.oslo import base as oslo_base
from oslo_config import cfg


from gcl_sdk.agents.universal.clients.orch import db as orch_db
from gcl_sdk.agents.universal.services import agent as agent_service
from gcl_sdk.agents.universal.services import scheduler as scheduler_service
from gcl_sdk.agents.universal import utils as ua_utils
from gcl_sdk.agents.universal.drivers import core as core_drivers
from genesis_db.common import constants as cc

LOG = logging.getLogger(__name__)


class InfraScheduler(
    scheduler_service.UniversalAgentSchedulerService,
    oslo_base.OsloConfigurableService,
):
    @classmethod
    def svc_get_config_opts(cls) -> tp.Collection[cfg.Opt]:
        return [
            cfg.ListOpt(
                "capabilities",
                default=tuple(),
                help=("List of capabilities to run."),
            )
        ]


class UAgent(agent_service.UniversalAgentService, oslo_base.OsloConfigurableService):
    def __init__(
        self,
        *args,
        core_username,
        core_password,
        core_api_base_url,
        project_id,
        **kwargs,
    ):
        agent_uuid = ua_utils.system_uuid()
        orch_client = orch_db.DatabaseOrchClient()
        core_driver = core_drivers.RestCoreCapabilityDriver(
            username=core_username,
            password=core_password,
            user_api_base_url=core_api_base_url,
            project_id=sys_uuid.UUID(project_id),
            use_project_scope=True,
            node_set="/v1/compute/sets/",
            config="/v1/config/configs/",
        )

        caps_drivers = [
            core_driver,
        ]

        facts_drivers = []
        payload_path = os.path.join(cc.WORK_DIR, "infra_agent_payload.json")
        return super().__init__(
            *args,
            agent_uuid=agent_uuid,
            orch_client=orch_client,
            caps_drivers=caps_drivers,
            facts_drivers=facts_drivers,
            payload_path=payload_path,
            **kwargs,
        )

    @classmethod
    def svc_get_config_opts(cls) -> tp.Collection[cfg.Opt]:
        return [
            cfg.StrOpt(
                "core_username",
                default="genesis_db",
                help=("User to work with Core."),
            ),
            cfg.StrOpt(
                "core_password",
                default="genesis_db",
                help=("User password to work with Core."),
            ),
            cfg.StrOpt(
                "core_api_base_url",
                default="http://10.20.0.2:11010",
                help=("Core's user api endpoint."),
            ),
            cfg.StrOpt(
                "project_id",
                help=("Project id to work with Core."),
            ),
        ]
