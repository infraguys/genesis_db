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

from restalchemy.api import routes

from genesis_db.user_api.api import controllers


# class DatabaseInstanceRoute(routes.Route):
#     __controller__ = controllers.DatabaseInstanceController


class DatabaseRoute(routes.Route):
    __controller__ = controllers.DatabaseController


class UserRoute(routes.Route):
    __controller__ = controllers.UserController


class PGInstanceRoute(routes.Route):
    __controller__ = controllers.PGInstanceController

    # route to /v1/types/postgres/instances/<uuid>/database/[<uuid>]
    databases = routes.route(DatabaseRoute, resource_route=True)
    # route to /v1/types/postgres/instances/<uuid>/users/[<uuid>]
    users = routes.route(UserRoute, resource_route=True)


class RoleRoute(routes.Route):
    __controller__ = controllers.RoleController


class RolePrivilegeRoute(routes.Route):
    __controller__ = controllers.RolePrivilegeController


class PGVersionRoute(routes.Route):
    __controller__ = controllers.PGVersionController


class PGRoute(routes.Route):

    __controller__ = controllers.PGController
    __allow_methods__ = [routes.FILTER]

    # route to /v1/types/postgres/instances/[<uuid>]
    instances = routes.route(PGInstanceRoute)

    # route to /v1/types/postgres/roles/[<uuid>]
    roles = routes.route(RoleRoute)

    # route to /v1/types/postgres/role_privileges/[<uuid>]
    role_privileges = routes.route(RolePrivilegeRoute)

    # route to /v1/types/postgres/versions/[<uuid>]
    versions = routes.route(PGVersionRoute)


class TypeRoute(routes.Route):
    """Handler for /v1/types/ endpoint"""

    __controller__ = controllers.TypeController
    __allow_methods__ = [routes.FILTER]

    # route to /v1/types/postgres/
    postgres = routes.route(PGRoute)


class ApiEndpointRoute(routes.Route):
    """Handler for /v1/ endpoint"""

    __controller__ = controllers.ApiEndpointController
    __allow_methods__ = [routes.FILTER]

    types = routes.route(TypeRoute)
