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

from restalchemy.dm import models
from restalchemy.dm import properties
from restalchemy.dm import relationships
from restalchemy.dm import types
from restalchemy.storage.sql import orm


class PGStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"


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
    disk_size = properties.property(types.Integer(min_value=1, max_value=1024**3))
    nodes_number = properties.property(types.Integer(min_value=1, max_value=16))
    sync_replica_number = properties.property(types.Integer(min_value=0, max_value=15))
    version = relationships.relationship(PGVersion, required=True)


class PGDatabase(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):

    __tablename__ = "postgres_databases"

    name = properties.property(types.String(min_length=1, max_length=255))
    instance = relationships.relationship(PGInstance, required=True)


# TODO: there may be other database types
# class DatabaseInstance(models.ModelWithUUID, orm.SQLStorableMixin):
#     database = relationships.relationship(Database, required=True)



class PGUser(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):

    __tablename__ = "postgres_users"
    name = properties.property(types.String(min_length=1, max_length=64))
    password = properties.property(types.String(min_length=8, max_length=256))
    instance = relationships.relationship(PGInstance, required=True)

class PGRole(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithProject,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):

    __tablename__ = "postgres_roles"

    name = properties.property(types.String(min_length=1, max_length=255))


# TODO: actually it's a role model for PG, may not be suited well for other DBs
class PGPrivilege(enum.Enum):
    ALL = "ALL"
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RULE = "RULE"
    REFERENCES = "REFERENCES"
    TRIGGER = "TRIGGER"
    CREATE = "CREATE"
    TEMPORARY = "TEMPORARY"
    EXECUTE = "EXECUTE"
    USAGE = "USAGE"


class PGRolePrivilege(
    models.ModelWithUUID,
    models.ModelWithNameDesc,
    models.ModelWithProject,
    models.ModelWithTimestamp,
    orm.SQLStorableMixin,
):

    __tablename__ = "postgres_role_privileges"
    role = relationships.relationship(PGRole, required=True)
    privilege = properties.property(
        types.Enum([v.value for v in PGPrivilege]),
        default=PGPrivilege.ALL.value,
    )
