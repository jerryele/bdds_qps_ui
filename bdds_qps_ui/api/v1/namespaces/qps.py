# Copyright 2026 BlueCat Networks (USA) Inc. and its affiliates. All Rights Reserved.
"""
REST endpoints for BDDS DNS/DHCP performance statistics, backed by BAM's built-in Prometheus.
"""
from datetime import datetime

from flask import request
from flask_restx import Namespace, Resource

from ..services.qps_service import QPSService
from ..services import bam_service
from ..utils.exceptions import PrometheusQueryError

stats_ns = Namespace("stats", description="BDDS DNS/DHCP performance statistics")


def _parse_iso(value: str) -> datetime:
    # `datetime.fromisoformat` only accepts a trailing "Z" from Python 3.11 onward; this
    # workflow runs on 3.9, so normalize it to an explicit UTC offset first.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@stats_ns.route("/configurations")
class ConfigurationList(Resource):
    """List the BAM configurations available to scope the server list to."""

    def get(self):
        return {"configurations": bam_service.list_configurations()}, 200


@stats_ns.route("/servers")
class ServerList(Resource):
    """List the BDDS servers currently reporting statistics to BAM's Prometheus."""

    def get(self):
        configuration = request.args.get("configuration")
        try:
            return {"servers": QPSService().list_servers(configuration)}, 200
        except PrometheusQueryError as e:
            return {"error": str(e)}, 502


@stats_ns.route("/current")
class CurrentStats(Resource):
    """
    Current DNS QPS and DHCP LPS.

    Accepts a repeated `?server=<exported_instance>` query param to scope to one or more
    servers, and/or `?configuration=<id>` to scope to a BAM configuration. With neither,
    every reporting server is included.
    """

    def get(self):
        servers = request.args.getlist("server")
        configuration = request.args.get("configuration")
        try:
            return QPSService().get_qps(servers, configuration), 200
        except PrometheusQueryError as e:
            return {"error": str(e)}, 502


@stats_ns.route("/history")
class HistoryStats(Resource):
    """
    DNS QPS time series over a time window, one series per server.

    Accepts the same `?server=` / `?configuration=` scoping as `/current`, plus optional
    `?start=` / `?end=` ISO 8601 timestamps. With neither, defaults to the last 60 minutes.
    """

    def get(self):
        servers = request.args.getlist("server")
        configuration = request.args.get("configuration")
        start_param = request.args.get("start")
        end_param = request.args.get("end")
        try:
            start = _parse_iso(start_param) if start_param else None
            end = _parse_iso(end_param) if end_param else None
        except ValueError:
            return {"error": "start/end must be ISO 8601 timestamps"}, 400
        try:
            return QPSService().get_history(servers, configuration, start, end), 200
        except PrometheusQueryError as e:
            return {"error": str(e)}, 502
