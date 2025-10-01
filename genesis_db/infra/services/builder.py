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

from gcl_sdk.infra.services import builder
from gcl_sdk.infra import constants as sdk_c
from gcl_sdk.infra.dm import models as sdk_models
from gcl_sdk.agents.universal.dm import models as ua_models

from genesis_db.infra.dm import models

LOG = logging.getLogger(__name__)
NODE_KIND = sdk_models.Node.get_resource_kind()
NODE_SET_KIND = sdk_models.NodeSet.get_resource_kind()
CONFIG_KIND = sdk_models.Config.get_resource_kind()

PATRONI_RAFT_PORT = 5010


PATRONI_CONF_TEMPLATE = """\
scope: "{cluster_name}"
namespace: /db/
name: "{node_name}"

restapi:
  listen: "0.0.0.0:8008"
  connect_address: "{node_ip}:8008"
  authentication:
    username: patroni
    password: patroni

raft:
  data_dir: /var/lib/postgresql/patroni/raft/
  self_addr: "{node_ip}:5010"
  partner_addrs: {raft_partner_addrs}

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: false
      use_slots: true
      parameters:
    synchronous_mode: {sync_mode}
    synchronous_mode_strict: {sync_mode}
    synchronous_node_count: {sync_replica_number}

  initdb:
  - encoding: UTF8
  - data-checksums
  - auth-local: peer
  - auth-host: scram-sha-256

postgresql:
  listen: "0.0.0.0:5432"
  connect_address: "{node_ip}:5432"
  data_dir: /var/lib/postgresql/patroni/data/
  bin_dir: /usr/sbin
  pgpass: /tmp/pgpass0
  authentication:
    replication:
      username: dbaas_replicator
      password: replicate_password
    superuser:
      username: postgres
      password: my-super-password
    rewind:
      username: dbaas_rewinder
      password: rewind_password
  parameters:
    unix_socket_directories: '/var/run/postgresql,/tmp'
    io_method: 'io_uring'
  pg_hba:
  - host replication dbaas_replicator 0.0.0.0/0 scram-sha-256
  - host all all 0.0.0.0/0 scram-sha-256
  - local all all peer map=genesis_map
  pg_ident:
   - genesis_map root postgres
   - genesis_map postgres postgres
watchdog:
  mode: required
  device: /dev/watchdog
  safety_margin: 5

tags:
  nofailover: false
  noloadbalance: false
  clonefrom: false
  nosync: false
"""


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
        nodeset = None
        configs = []

        for target, actual in infra.infra_objects:
            if target.get_resource_kind() == NODE_SET_KIND:
                nodeset = actual
            elif actual.get_resource_kind() == CONFIG_KIND:
                configs.append(actual)

        if nodeset.status != sdk_c.NodeStatus.ACTIVE.value:
            return infra.targets()

        new_objects = []

        node_raft_members = [
            f"{node['ipv4']}:{PATRONI_RAFT_PORT}"
            for node in nodeset.nodes.values()
        ]
        # In case of shrink we still has all nodes but only lower nodes_number
        if (diff_num := len(node_raft_members) - instance.nodes_number) > 0:
            node_raft_members = node_raft_members[:-diff_num]

        sync_mode = "true" if instance.sync_replica_number else "false"

        for node_uuid, node in nodeset.nodes.items():
            content = PATRONI_CONF_TEMPLATE.format(
                cluster_name=instance.name,
                node_name=node_uuid,
                node_ip=node["ipv4"],
                raft_partner_addrs=node_raft_members,
                sync_mode=sync_mode,
                sync_replica_number=instance.sync_replica_number,
                on_change=instance.OnReloadFunc,
            )
            config = instance._create_config(
                uuid.UUID(node_uuid), self._project_id, content
            )
            new_objects.append(config)

        # Update config content
        for target, _ in infra.infra_objects:
            if target.get_resource_kind() == CONFIG_KIND:
                content = PATRONI_CONF_TEMPLATE.format(
                    cluster_name=instance.name,
                    node_name=target.target.node,
                    node_ip=nodeset.nodes[str(target.target.node)]["ipv4"],
                    raft_partner_addrs=node_raft_members,
                    sync_mode=sync_mode,
                    sync_replica_number=instance.sync_replica_number,
                    on_change=instance.OnReloadFunc,
                )
                if target.body.content != content:
                    target.body.content = content
            elif target.get_resource_kind() == NODE_SET_KIND:
                target.cores = instance.cpu
                target.ram = instance.ram
                target.image = instance.version.image
                target.replicas = instance.nodes_number
                # This action wipe out the disk.
                # Rethink this part when we have persistent volumes.
                # target.root_disk_size = instance.disk_size

        instance.ipsv4 = [node["ipv4"] for node in nodeset.nodes.values()]

        try:
            instance.status = sdk_c.InstanceStatus(nodeset.status).value
        except ValueError:
            instance.status = sdk_c.InstanceStatus.IN_PROGRESS.value

        # Return the target resources
        if new_objects:
            return (*infra.targets(), *new_objects)
        return infra.targets()
