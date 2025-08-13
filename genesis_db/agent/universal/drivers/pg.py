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

import logging

from restalchemy.dm import types as ra_types
from restalchemy.dm import properties
from gcl_sdk.agents.universal.drivers import meta
from gcl_sdk.agents.universal.drivers import exceptions as driver_exc


LOG = logging.getLogger(__name__)


class PGDatabase(meta.MetaDataPlaneModel):

    __storage__ = {}

    name = properties.property(ra_types.String(min_length=1, max_length=255))

    def get_meta_model_fields(self) -> set[str] | None:
        """Return a list of meta fields or None.

        Meta fields are the fields that cannot be fetched from
        the data plane or we just want to save them into the meta file.

        `None` means all fields are meta fields but it doesn't mean they
        won't be updated from the data plane.
        """
        return {"uuid", "name"}

    def dump_to_dp(self) -> None:
        """Save the resource to the data plane."""
        view = self.dump_to_simple_view()
        self.__storage__[self.uuid] = view

    def restore_from_dp(self) -> None:
        """Load the render from the file system."""
        LOG.warning("RESTORE -> %s", self.__storage__)
        if self.uuid not in self.__storage__:
            raise driver_exc.ResourceNotFound(
                resource=self.to_ua_resource("pg_database_node")
            )

    def delete_from_dp(self) -> None:
        """Delete the resource from the data plane."""
        del self.__storage__[self.uuid]


class PGCapabilityDriver(meta.MetaFileStorageAgentDriver):
    """PG capability driver."""

    PG_META_PATH = "/var/lib/genesis/genesis_db/pg_meta.json"

    __model_map__ = {"pg_database_node": PGDatabase}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, meta_file=self.PG_META_PATH, **kwargs)
