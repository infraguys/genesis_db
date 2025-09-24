#    Copyright 2016 Eugene Frolov <eugene@frolov.net.ru>
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

from restalchemy.storage.sql import migrations


class MigrationStep(migrations.AbstarctMigrationStep):

    def __init__(self):
        self._depends = []

    @property
    def migration_id(self):
        return "63a338db-a04b-4fce-bf47-3ed00660a6f4"

    @property
    def is_manual(self):
        return False

    def upgrade(self, session):
        expressions = [
            """\
CREATE TABLE postgres_versions (
    uuid UUID PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    image TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
""",
            """\
CREATE TABLE postgres_instances (
    uuid UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_id UUID NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'NEW',
    cpu INT NOT NULL CHECK (cpu BETWEEN 1 AND 128),
    ram INT NOT NULL CHECK (ram BETWEEN 512 AND 1073741824),
    disk_size INT NOT NULL CHECK (disk_size BETWEEN 1 AND 1073741824),
    nodes_number INT NOT NULL CHECK (nodes_number BETWEEN 1 AND 16),
    sync_replica_number INT NOT NULL CHECK (sync_replica_number BETWEEN 0 AND 15),
    version UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (version) REFERENCES postgres_versions(uuid)
);

CREATE INDEX ON postgres_instances(project_id, name);
""",
            """\
CREATE TABLE postgres_users (
    uuid UUID PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'NEW',
    description TEXT,
    project_id UUID NOT NULL,
    password VARCHAR(256) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    instance UUID NOT NULL,
    FOREIGN KEY (instance) REFERENCES postgres_instances(uuid)
);
""",
            """\
CREATE TABLE postgres_databases (
    uuid UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'NEW',
    description TEXT,
    project_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    instance UUID NOT NULL,
    owner UUID NOT NULL,
    FOREIGN KEY (instance) REFERENCES postgres_instances(uuid),
    FOREIGN KEY ("owner") REFERENCES postgres_users(uuid)
);
""",
            """\
CREATE INDEX IF NOT EXISTS postgres_users_project_id_idx
                ON postgres_users (project_id);
""",
            """\
CREATE INDEX IF NOT EXISTS postgres_databases_project_id_idx
                ON postgres_databases (project_id);
""",
        ]

        for expression in expressions:
            session.execute(expression)

    def downgrade(self, session):

        tables = [
            # "postgres_user_privileges",
            "postgres_databases",
            "postgres_users",
            "postgres_instances",
            "postgres_versions",
        ]

        for table in tables:
            self._delete_table_if_exists(session, table)


migration_step = MigrationStep()
