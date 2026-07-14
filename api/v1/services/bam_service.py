# Copyright 2026 BlueCat Networks (USA) Inc. and its affiliates. All Rights Reserved.
"""
Helpers for reading BAM configuration/server inventory, used to scope and label the
BDDS servers shown by the QPS Statistics page.
"""
from urllib.parse import urlparse

from flask import g

from ..utils.constants import PROMETHEUS_PORT


def get_prometheus_base_url() -> str:
    """
    Return BAM's Prometheus base URL.

    The host is read off the same BAM connection this Gateway is already configured
    with (`g.user.get_api()`), rather than a hardcoded address, since BAM's Prometheus
    always runs alongside BAM on that host.
    """
    bam_host = urlparse(g.user.get_api().get_url()).hostname
    return f"http://{bam_host}:{PROMETHEUS_PORT}"


def list_configurations() -> list:
    """Return every BAM configuration as {"id": ..., "name": ...}."""
    configs = g.user.get_api().get_configurations()
    return [{"id": str(c.get_id()), "name": c.get_name()} for c in configs]


def list_server_ids(configuration_id: str) -> set:
    """
    Return the BAM entity IDs (as strings) of every server under a configuration.

    These IDs match the `server_id` label BAM's Prometheus exporter tags each server's
    metrics with, so this is what lets the QPS Statistics page scope its server list to
    a single configuration.
    """
    api = g.user.get_api()
    for configuration in api.get_configurations():
        if str(configuration.get_id()) == str(configuration_id):
            return {str(server.get_id()) for server in configuration.get_servers()}
    return set()
