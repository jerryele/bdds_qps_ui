# Copyright 2026 BlueCat Networks (USA) Inc. and its affiliates. All Rights Reserved.
"""
Minimal HTTP client for querying BAM's built-in Prometheus server.

BDDS servers each expose raw metrics on their own :10048 port behind mutual TLS, and
that port is not meant to be reached directly. BAM's Prometheus (installed alongside BAM)
scrapes every managed BDDS on our behalf and aggregates the results, so this workflow only
ever talks to BAM's Prometheus HTTP API, never to a BDDS directly.
"""
import requests

from ..utils.constants import PROMETHEUS_TIMEOUT_SECONDS
from ..utils.exceptions import PrometheusQueryError


class PrometheusClient:
    """Thin wrapper around Prometheus's HTTP query API."""

    def __init__(self, base_url: str, timeout: int = PROMETHEUS_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def instant_query(self, promql: str) -> list:
        """
        Run an instant PromQL query and return the list of result series.

        :param promql: The PromQL expression to evaluate.
        :return: The `data.result` list from Prometheus's response.
        :raises PrometheusQueryError: On any connection, HTTP, or Prometheus API error.
        """
        return self._get("/api/v1/query", {"query": promql})

    def range_query(self, promql: str, start: float, end: float, step: str) -> list:
        """
        Run a PromQL range query and return the list of result series.

        :param promql: The PromQL expression to evaluate.
        :param start: Start of the window, as a Unix timestamp in seconds.
        :param end: End of the window, as a Unix timestamp in seconds.
        :param step: Query resolution step width, e.g. "60s".
        :return: The `data.result` list from Prometheus's response, each entry carrying
            a `values` list of `[timestamp, value]` pairs rather than a single `value`.
        :raises PrometheusQueryError: On any connection, HTTP, or Prometheus API error.
        """
        return self._get(
            "/api/v1/query_range",
            {"query": promql, "start": start, "end": end, "step": step},
        )

    def _get(self, path: str, params: dict) -> list:
        try:
            resp = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise PrometheusQueryError(f"Failed to reach Prometheus at {self.base_url}: {e}") from e

        payload = resp.json()
        if payload.get("status") != "success":
            raise PrometheusQueryError(f"Prometheus query failed: {payload.get('error', payload)}")

        return payload["data"]["result"]
