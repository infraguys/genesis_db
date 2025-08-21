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

from restalchemy.api import applications
from restalchemy.api import middlewares
from restalchemy.api import routes
from restalchemy.api.middlewares import contexts as context_mw
from restalchemy.api.middlewares import errors as errors_mw
from restalchemy.api.middlewares import logging as logging_mw
from restalchemy.openapi import structures as openapi_structures
from restalchemy.openapi import engines as openapi_engines

from genesis_db.status_api.api import routes as app_routes
from genesis_db.status_api.api import versions
from genesis_db import version


class StatusApiApp(routes.RootRoute):
    pass


# Route to /v1/ endpoint.
setattr(
    StatusApiApp,
    versions.API_VERSION_v1,
    routes.route(app_routes.ApiEndpointRoute),
)


def get_api_application():
    return StatusApiApp


def get_openapi_engine():
    openapi_engine = openapi_engines.OpenApiEngine(
        info=openapi_structures.OpenApiInfo(
            title=f"Genesis DB {versions.API_VERSION_v1} Status API",
            version=version.version_info.release_string(),
            description=f"OpenAPI - Genesis DB {versions.API_VERSION_v1}",
        ),
        paths=openapi_structures.OpenApiPaths(),
        components=openapi_structures.OpenApiComponents(),
    )
    return openapi_engine


def build_wsgi_application():
    return middlewares.attach_middlewares(
        applications.OpenApiApplication(
            route_class=get_api_application(),
            openapi_engine=get_openapi_engine(),
        ),
        [
            context_mw.ContextMiddleware,
            errors_mw.ErrorsHandlerMiddleware,
            logging_mw.LoggingMiddleware,
        ],
    )
