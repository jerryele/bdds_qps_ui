# Copyright 2026 BlueCat Networks (USA) Inc. and its affiliates. All Rights Reserved.
"""
Custom exceptions for the BDDS Performance Statistics API.
"""


class PrometheusQueryError(Exception):
    """Raised when a query against BAM's Prometheus server fails."""
