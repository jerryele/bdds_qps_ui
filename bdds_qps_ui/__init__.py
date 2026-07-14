# Copyright 2026 BlueCat Networks (USA) Inc. and its affiliates. All Rights Reserved.
"""
BDDS Performance Statistics workflow initialization.

Single workflow package providing both the navigable UI page (via `sub_pages`,
`type="ui"`) and the flask_restx REST API that page's JavaScript polls for data.
"""
from typing import Final

from flask import Blueprint
from flask_restx import Api
from main_app import app

# Define workflow metadata
type: str = "ui"  # noqa: A001
sub_pages: list[dict[str, str]] = [
    {
        "name": "bdds_qps_page",
        "title": "BDDS Performance Statistics",
        "endpoint": "bdds_qps_ui/page",
        "description": "Real-time DNS/DHCP performance statistics for BDDS servers",
    },
]

API_VERSION: Final[str] = "1.0"
API_PREFIX: Final[str] = "/bdds_qps/v1"

api_endpoints: Blueprint = Blueprint(
    "bdds_qps_api",  # Blueprint name
    "bdds_qps_api",  # Import name
)

bdds_qps_api: Api = Api(
    api_endpoints,
    version=API_VERSION,
    title="BDDS Performance Statistics API",
    description="REST API for retrieving BDDS DNS/DHCP performance metrics from BAM's built-in Prometheus",
    doc="/doc",
    default_label="BDDS Performance Statistics",
    validate=True,
)

# Register API blueprint with Flask app
app.register_blueprint(api_endpoints, url_prefix=API_PREFIX)

# Register API namespaces. Each namespace is mounted under its own name, e.g. the "stats"
# namespace's routes end up at API_PREFIX + "/stats/...".
from .api import v1

for namespace in v1.namespaces:
    bdds_qps_api.add_namespace(namespace)
