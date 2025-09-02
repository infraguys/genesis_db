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

import enum
import re

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.dm import types_dynamic
from restalchemy.storage.sql import orm

from genesis_db.common import utils as u


class PGStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"


class PGNameType(types.BaseCompiledRegExpTypeFromAttr):
    # https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-IDENTIFIERS
    pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


class PGVersion(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "postgres_versions"

    image = properties.property(types.String(max_length=2048))


class PGInstance(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithProject,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):
    __tablename__ = "postgres_instances"

    name = properties.property(types.String(min_length=1, max_length=255))
    status = properties.property(
        types.Enum([status.value for status in PGStatus]),
        default=PGStatus.NEW.value,
    )
    cpu = properties.property(types.Integer(min_value=1, max_value=128))
    ram = properties.property(types.Integer(min_value=512, max_value=1024**3))
    disk_size = properties.property(
        types.Integer(min_value=1, max_value=1024**3)
    )
    # TODO: restrict shrink/support shrink
    nodes_number = properties.property(
        types.Integer(min_value=1, max_value=16)
    )
    sync_replica_number = properties.property(
        types.Integer(min_value=0, max_value=15)
    )
    version = relationships.relationship(
        PGVersion, required=True, read_only=True
    )

    def delete(self, session=None, **kwargs):
        u.remove_nested_dm(PGDatabase, "instance", self, session=session)
        u.remove_nested_dm(PGUser, "instance", self, session=session)
        return super().delete(session=session, **kwargs)


class PGUser(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):

    __tablename__ = "postgres_users"
    # TODO: restrict system users (postgres, replicator, rewind_user)
    name = properties.property(PGNameType(), required=True, read_only=True)
    status = properties.property(
        types.Enum([status.value for status in PGStatus]),
        default=PGStatus.NEW.value,
    )
    password = properties.property(types.String(min_length=8, max_length=99))
    instance = relationships.relationship(
        PGInstance, required=True, read_only=True
    )

    def delete(self, session=None, **kwargs):
        # u.remove_nested_dm(PGUserPrivilege, "user", self, session=session)
        return super().delete(session=session, **kwargs)


class PGDatabase(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):

    __tablename__ = "postgres_databases"

    name = properties.property(PGNameType(), required=True)
    status = properties.property(
        types.Enum([status.value for status in PGStatus]),
        default=PGStatus.NEW.value,
    )
    instance = relationships.relationship(PGInstance, required=True)
    owner = relationships.relationship(PGUser, required=True)

    def delete(self, session=None, **kwargs):
        # u.remove_nested_dm(PGUserPrivilege, "database", self, session=session)
        return super().delete(session=session, **kwargs)


# class PGDatabasePrivilege(str, enum.Enum):
#     ALL = "ALL"
#     CREATE = "CREATE"
#     CONNECT = "CONNECT"
#     TEMPORARY = "TEMPORARY"


# class PGTablePrivilege(str, enum.Enum):
#     ALL = "ALL"
#     SELECT = "SELECT"
#     INSERT = "INSERT"
#     UPDATE = "UPDATE"
#     DELETE = "DELETE"
#     TRUNCATE = "TRUNCATE"
#     REFERENCES = "REFERENCES"
#     TRIGGER = "TRIGGER"
#     MAINTAIN = "MAINTAIN"


# class DatabaseEntity(types_dynamic.AbstractKindModel):
#     KIND = "DATABASE"

#     privileges = properties.property(
#         types.TypedList(types.Enum([v.value for v in PGDatabasePrivilege])),
#         default=[PGDatabasePrivilege.ALL.value],
#     )

#     @property
#     def name(self):
#         # TODO: different kinds (for ex. tables) will have `name` prop
#         return ""


# class PGUserPrivilege(
#     models.ModelWithUUID,
#     models.ModelWithTimestamp,
#     orm.SQLStorableMixin,
# ):

#     __tablename__ = "postgres_user_privileges"
#     user = relationships.relationship(PGUser, required=True)
#     database = relationships.relationship(PGDatabase, required=True)
#     entity = properties.property(
#         types_dynamic.KindModelSelectorType(
#             types_dynamic.KindModelType(DatabaseEntity),
#         ),
#         required=True,
#     )
