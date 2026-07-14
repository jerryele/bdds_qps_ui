# Copyright 2026 BlueCat Networks (USA) Inc. and its affiliates. All Rights Reserved.
"""
Business logic for retrieving BDDS QPS/LPS statistics from BAM's Prometheus.
"""
from datetime import datetime, timedelta, timezone

from . import bam_service
from .prometheus_client import PrometheusClient
from ..utils.constants import BDDS_JOB_LABEL, DNS_REQUEST_NSSTATS, POLL_INTERVAL_SECONDS


class QPSService:
    """Reads DNS/DHCP performance counters for BDDS servers out of BAM's Prometheus."""

    def __init__(self, client: PrometheusClient = None):
        self.client = client or PrometheusClient(bam_service.get_prometheus_base_url())

    def list_servers(self, configuration: str = None) -> list:
        """
        Return the BDDS servers currently reporting DNS statistics to Prometheus.

        :param configuration: A BAM configuration ID. When given, the list is scoped to
            servers that belong to that configuration; when omitted, every reporting
            BDDS is returned.
        """
        promql = f'group by (exported_instance, instance, server_id) (bc_dns_nsstats_since_poll{{job="{BDDS_JOB_LABEL}"}})'
        result = self.client.instant_query(promql)
        servers = [self._server_labels(series["metric"]) for series in result]

        if configuration:
            allowed_ids = bam_service.list_server_ids(configuration)
            servers = [s for s in servers if s["server_id"] in allowed_ids]

        return servers

    def get_qps(self, servers: list = None, configuration: str = None) -> dict:
        """
        Return current DNS QPS and DHCP LPS.

        :param servers: A list of `exported_instance` label values to filter to. When
            empty or omitted, every server in scope is included.
        :param configuration: A BAM configuration ID to scope the server list to (see
            `list_servers`). Ignored if `servers` is given.
        """
        all_servers = self.list_servers(configuration)
        if servers:
            wanted = set(servers)
            all_servers = [s for s in all_servers if s["exported_instance"] in wanted]

        stats = [self._read_server_stats(s) for s in all_servers]
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
            "servers": stats,
        }

    def get_history(
        self,
        servers: list = None,
        configuration: str = None,
        start: datetime = None,
        end: datetime = None,
    ) -> dict:
        """
        Return DNS-QPS and DHCP-LPS time series between `start` and `end`, one series per
        server per metric.

        :param servers: A list of `exported_instance` label values to filter to. When
            empty or omitted, every server in scope is included.
        :param configuration: A BAM configuration ID to scope the server list to (see
            `list_servers`). Ignored if `servers` is given.
        :param start: Start of the window (defaults to `end` minus 60 minutes).
        :param end: End of the window (defaults to now).
        """
        all_servers = self.list_servers(configuration)
        if servers:
            wanted = set(servers)
            all_servers = [s for s in all_servers if s["exported_instance"] in wanted]

        end = end or datetime.now(timezone.utc)
        start = start or (end - timedelta(minutes=60))
        step_seconds = self._pick_step_seconds((end - start).total_seconds())
        step = f"{step_seconds}s"
        nsstat_filter = "|".join(DNS_REQUEST_NSSTATS)

        dns_qps_series = []
        dhcp_lps_series = []
        for s in all_servers:
            instance_filter = f'exported_instance="{s["exported_instance"]}"'

            dns_promql = f'sum(bc_dns_nsstats_since_poll{{{instance_filter}, nsstat=~"{nsstat_filter}"}})'
            dns_result = self.client.range_query(dns_promql, start.timestamp(), end.timestamp(), step)
            # The metric is always "count over the last poll interval" regardless of the
            # query step above, so the QPS conversion always divides by the poll interval,
            # never by `step_seconds` (a coarser step only thins out how often we sample it).
            dns_qps_series.append({
                "exported_instance": s["exported_instance"],
                "points": self._to_points(dns_result, scale=1 / POLL_INTERVAL_SECONDS),
            })

            dhcp_promql = f"bc_dhcp4_leases_per_second{{{instance_filter}}}"
            dhcp_result = self.client.range_query(dhcp_promql, start.timestamp(), end.timestamp(), step)
            dhcp_lps_series.append({
                "exported_instance": s["exported_instance"],
                "points": self._to_points(dhcp_result),
            })

        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "step_seconds": step_seconds,
            "series": {
                "dns_qps": dns_qps_series,
                "dhcp_lps": dhcp_lps_series,
            },
        }

    @staticmethod
    def _pick_step_seconds(span_seconds: float) -> int:
        """Coarsen the query step for longer windows, so long ranges stay a reasonable size."""
        if span_seconds <= 3600:
            return POLL_INTERVAL_SECONDS
        if span_seconds <= 24 * 3600:
            return 300
        if span_seconds <= 7 * 24 * 3600:
            return 3600
        return 7200

    def _read_server_stats(self, server: dict) -> dict:
        instance_filter = f'exported_instance="{server["exported_instance"]}"'

        # `bc_dns_nsstats_since_poll` is a per-scrape delta (see POLL_INTERVAL_SECONDS), so
        # summing the incoming-request counters and dividing by the poll interval gives an
        # average queries-per-second figure for that window.
        nsstat_filter = "|".join(DNS_REQUEST_NSSTATS)
        dns_promql = f'sum(bc_dns_nsstats_since_poll{{{instance_filter}, nsstat=~"{nsstat_filter}"}})'
        dns_requests = self._first_value(self.client.instant_query(dns_promql))

        # `bc_dhcp4_leases_per_second` is already a computed rate, no conversion needed.
        dhcp_promql = f"bc_dhcp4_leases_per_second{{{instance_filter}}}"
        dhcp_lps = self._first_value(self.client.instant_query(dhcp_promql))

        return {
            **server,
            "dns_qps": round(dns_requests / POLL_INTERVAL_SECONDS, 2) if dns_requests is not None else None,
            "dhcp_lps": round(dhcp_lps, 2) if dhcp_lps is not None else None,
        }

    @staticmethod
    def _server_labels(metric: dict) -> dict:
        return {
            "exported_instance": metric.get("exported_instance"),
            "instance": metric.get("instance"),
            "server_id": metric.get("server_id"),
        }

    @staticmethod
    def _first_value(result: list):
        if not result:
            return None
        return float(result[0]["value"][1])

    @staticmethod
    def _to_points(result: list, scale: float = 1.0) -> list:
        if not result:
            return []
        return [{"t": int(v[0]), "v": round(float(v[1]) * scale, 2)} for v in result[0]["values"]]
