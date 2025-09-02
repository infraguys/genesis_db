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

from functools import lru_cache
from functools import wraps
import logging
import requests
import time

from restalchemy.dm import types as ra_types
from restalchemy.dm import properties
from gcl_sdk.agents.universal.drivers import base
from gcl_sdk.agents.universal.drivers import meta
from gcl_sdk.agents.universal.drivers import exceptions as driver_exc
from gcl_sdk.agents.universal import constants as c
import psycopg
from psycopg import sql

from restalchemy.common import singletons
from restalchemy.dm import properties


from genesis_db.common import constants
from genesis_db.common.pg_auth import passwd


LOG = logging.getLogger(__name__)


def get_ttl_hash(seconds=600):
    """Return the same value withing `seconds` time period"""
    return round(time.time() / seconds)


class PatroniClient:
    def __init__(self):
        self._endpoint = constants.PATRONI_API_ENDPOINT
        # We don't need retries/etc because it's local and patroni loves to
        #  return 5XX codes with valid responses
        #  https://patroni.readthedocs.io/en/latest/rest_api.html
        self._client = requests.Session()

    def get_full_state(self):
        return self._client.get(f"{self._endpoint}/").json()

    @lru_cache()
    def is_primary(self, ttl_hash=None):
        del ttl_hash
        return self._client.get(f"{self._endpoint}/primary").status_code == 200


class ClientsSingleton(singletons.InheritSingleton):

    def __init__(self):
        self.reinit_pclient()
        self.reinit_psql()

    def reinit_pclient(self):
        self._pclient = PatroniClient()

    def reinit_psql(self):
        # It's important to log all pg queries here
        logging.getLogger("psycopg").setLevel(logging.DEBUG)
        # We need to run this agent from Linux user with peer access to pg
        self._psql = psycopg.connect("user=postgres", autocommit=True)

    @property
    def pclient(self):
        return self._pclient

    @property
    def psql(self):
        if self._psql.broken or self._psql.closed:
            self.reinit_psql()
        return self._psql


def on_primary_only(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        if self.c.pclient.is_primary(get_ttl_hash(seconds=20)):
            return method(self, *method_args, **method_kwargs)
        LOG.debug("Not a primary node, skipping %s call.", method.__name__)

    return _impl


class PGUser(meta.MetaDataPlaneModel):

    name = properties.property(ra_types.String(min_length=1, max_length=64))
    password_hash = properties.property(
        ra_types.String(min_length=8, max_length=256)
    )

    _meta_fields = {"uuid", "name"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.c = ClientsSingleton()

    def get_meta_model_fields(self) -> set[str] | None:
        return self._meta_fields

    @on_primary_only
    def dump_to_dp(self) -> None:
        res = self.c.psql.execute(
            "SELECT rolname, rolpassword FROM pg_authid WHERE rolname=%s",
            (self.name,),
        ).fetchall()

        escaped_password = "'{}'".format(self.password_hash.replace("'", "''"))

        if len(res) == 0:
            self.c.psql.execute(
                sql.SQL(
                    "CREATE USER {username} WITH PASSWORD {password}"
                ).format(
                    username=sql.Identifier(self.name),
                    password=sql.Literal(
                        self.password_hash.replace("'", "''")
                    ),
                )
            )

            LOG.info("User %s created", self.name)
            return

        dname, dpasshash = res[0]

        if self.password_hash != dpasshash:
            self.c.psql.execute(
                sql.SQL(
                    "ALTER USER {username} WITH PASSWORD {password}"
                ).format(
                    username=sql.Identifier(self.name),
                    password=sql.Literal(
                        self.password_hash.replace("'", "''")
                    ),
                )
            )

            LOG.info("User %s: password updated", self.name)
            return

        LOG.info("User %s with actual pass already exists", self.name)
        return

    @on_primary_only
    def restore_from_dp(self) -> None:
        res = self.c.psql.execute(
            "SELECT rolname, rolpassword FROM pg_authid WHERE rolname=%s",
            (self.name,),
        ).fetchall()

        if len(res) != 1:
            resource = self.to_ua_resource("pg_user_node")
            raise driver_exc.ResourceNotFound(resource=resource)

        self.password_hash = res[0][1]

    @on_primary_only
    def delete_from_dp(self) -> None:
        self.c.psql.execute(
            sql.SQL("DROP USER IF EXISTS {}").format(sql.Identifier(self.name))
        )

        LOG.info("User %s dropped", self.name)

    @on_primary_only
    def update_on_dp(self) -> None:
        self.dump_to_dp()


class PGDatabase(meta.MetaDataPlaneModel):

    name = properties.property(
        ra_types.String(min_length=1, max_length=512),
        required=True,
    )
    owner = properties.property(ra_types.String(min_length=1, max_length=64))

    _meta_fields = {"uuid", "name"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.c = ClientsSingleton()

    def get_meta_model_fields(self) -> set[str] | None:
        return self._meta_fields

    @on_primary_only
    def dump_to_dp(self) -> None:
        res = self.c.psql.execute(
            """\
SELECT d.datname as "name",
pg_catalog.pg_get_userbyid(d.datdba) as "owner"
FROM pg_catalog.pg_database d
WHERE d.datname = %s""",
            (self.name,),
        ).fetchall()

        if len(res) == 1:
            LOG.info("Database %s already exists", self.name)

            if res[0][1] != self.owner:
                self.c.psql.execute(
                    sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                        sql.Identifier(self.name), sql.Literal(self.owner)
                    )
                )
                LOG.info(
                    "Owner of database %s altered to %s", self.name, self.owner
                )

            return

        self.c.psql.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(self.name), sql.Literal(self.owner)
            )
        )

        LOG.info("Database %s created", self.name)

    @on_primary_only
    def restore_from_dp(self) -> None:
        res = self.c.psql.execute(
            """\
SELECT d.datname as "name",
pg_catalog.pg_get_userbyid(d.datdba) as "owner"
FROM pg_catalog.pg_database d
WHERE d.datname = %s""",
            (self.name,),
        ).fetchall()

        if len(res) != 1:
            resource = self.to_ua_resource("pg_database_node")
            raise driver_exc.ResourceNotFound(resource=resource)

        self.owner = res[0][1]

    @on_primary_only
    def delete_from_dp(self) -> None:
        self.c.psql.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(self.name)
            )
        )

        LOG.info("Database %s dropped", self.name)

    @on_primary_only
    def update_on_dp(self) -> None:
        self.dump_to_dp()


# class Privilege(meta.MetaDataPlaneModel):

#     database = properties.property(
#         ra_types.String(min_length=1, max_length=255)
#     )
#     username = properties.property(
#         ra_types.String(min_length=1, max_length=64)
#     )
#     kind = properties.property(ra_types.String())
#     kind_name = properties.property(ra_types.String())
#     privileges = properties.property(ra_types.List())

#     _meta_fields = {
#         "uuid",
#         "database",
#         "username",
#         "kind",
#         "kind_name",
#         "privileges",
#     }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.c = ClientsSingleton()

#     def get_meta_model_fields(self) -> set[str] | None:
#         return self._meta_fields

#     @on_primary_only
#     def dump_to_dp(self) -> None:
#         # res = self.c.psql.execute(
#         #     "SELECT rolname, rolpassword FROM pg_authid WHERE rolname=%s",
#         #     (self.name,),
#         # ).fetchall()

#         # if len(res) == 0:
#         #     self.c.psql.execute(
#         #         "create user %s with password %s; ", (self.name, self.password)
#         #     )

#         #     LOG.info("User %s created", self.name)
#         #     return

#         # dname, dpasshash = res[0]

#         # if not passwd.verify_password(dname, self.password, dpasshash):
#         #     self.c.psql.execute(
#         #         "ALTER USER %s WITH PASSWORD %s", (self.name, self.password)
#         #     )

#         #     LOG.info("User %s: password updated", self.name)
#         #     return

#         # LOG.info("User %s with actual pass already exists", self.name)
#         return

#     @on_primary_only
#     def restore_from_dp(self) -> None:
#         # res = self.c.psql.execute(
#         #     "SELECT rolname, rolpassword FROM pg_authid WHERE rolname= %s",
#         #     (self.name,),
#         # ).fetchall()

#         # if len(res) != 1:
#         #     resource = self.to_ua_resource("user")
#         #     raise driver_exc.ResourceNotFound(resource=resource)

#         pass

#         # TODO: what to do with password?

#     @on_primary_only
#     def delete_from_dp(self) -> None:
#         self.c.psql.execute("DROP USER IF EXISTS %s", (self.name,))

#         LOG.info("User %s dropped", self.name)

#     @on_primary_only
#     def update_on_dp(self) -> None:
#         self.dump_to_dp()


class PGCapabilityDriver(meta.MetaFileStorageAgentDriver):
    """PG capability driver."""

    PG_META_PATH = "/var/lib/genesis/genesis_db/pg_meta.json"

    __model_map__ = {"pg_database_node": PGDatabase, "pg_user_node": PGUser}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, meta_file=self.PG_META_PATH, **kwargs)
