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

from gcl_iam import middlewares as iam_mw
from restalchemy.api import applications
from restalchemy.api.middlewares import logging as logging_mw
from restalchemy.api import middlewares
from restalchemy.api import routes
from restalchemy.openapi import structures as openapi_structures
from restalchemy.openapi import engines as openapi_engines

from genesis_db.common.api.middlewares import errors as errors_mw
from genesis_db.user_api.api import routes as app_routes
from genesis_db.user_api.api import versions
from genesis_db import version as app_version


skip_auth_endpoints = [
    iam_mw.EndpointComparator("/"),
    iam_mw.EndpointComparator("/v1/"),
]


class UserApiApp(routes.RootRoute):
    pass


# Route to /v1/ endpoint.
setattr(
    UserApiApp,
    versions.API_VERSION_1_0,
    routes.route(app_routes.ApiEndpointRoute),
)


def get_api_application():
    return UserApiApp


def get_openapi_engine():
    openapi_engine = openapi_engines.OpenApiEngine(
        info=openapi_structures.OpenApiInfo(
            title=f"Genesis Db {versions.API_VERSION_1_0} User API",
            version=app_version.version_info.release_string(),
            description=(f"OpenAPI - Genesis Db {versions.API_VERSION_1_0}"),
        ),
        paths=openapi_structures.OpenApiPaths(),
        components=openapi_structures.OpenApiComponents(),
    )
    return openapi_engine


def build_wsgi_application(token_algorithm, iam_engine_driver=None):
    return middlewares.attach_middlewares(
        applications.OpenApiApplication(
            route_class=get_api_application(),
            openapi_engine=get_openapi_engine(),
        ),
        [
            middlewares.configure_middleware(
                iam_mw.GenesisCoreAuthMiddleware,
                token_algorithm=token_algorithm,
                iam_engine_driver=iam_engine_driver,
                skip_auth_endpoints=skip_auth_endpoints,
            ),
            errors_mw.ErrorsHandlerMiddleware,
            logging_mw.LoggingMiddleware,
        ],
    )
