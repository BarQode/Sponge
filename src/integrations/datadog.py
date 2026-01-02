"""
DataDog integration for log and metrics collection.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import requests
from requests.exceptions import RequestException

from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class DataDogIntegration(BaseIntegration):
    """DataDog integration for comprehensive monitoring data."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize DataDog integration.

        Required config keys:
        - api_key: DataDog API key
        - app_key: DataDog application key
        - site: DataDog site (default: datadoghq.com)
        """
        super().__init__(config)

        self.api_key = config.get('api_key')
        self.app_key = config.get('app_key')
        self.site = config.get('site', 'datadoghq.com')

        if not self.api_key or not self.app_key:
            raise ValueError("DataDog API key and app key are required")

        self.base_url = f"https://api.{self.site}/api/v2"
        self.headers = {
            'DD-API-KEY': self.api_key,
            'DD-APPLICATION-KEY': self.app_key,
            'Content-Type': 'application/json'
        }

        logger.info(f"DataDog integration initialized for site: {self.site}")

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch logs from DataDog."""
        logs = []
        filters = filters or {}

        try:
            # Build query
            query = filters.get('query', '*')
            index = filters.get('index', '*')

            # DataDog uses milliseconds since epoch
            from_ts = int(start_time.timestamp() * 1000)
            to_ts = int(end_time.timestamp() * 1000)

            # API endpoint
            url = f"{self.base_url}/logs/events/search"

            payload = {
                'filter': {
                    'from': from_ts,
                    'to': to_ts,
                    'query': query,
                    'indexes': [index] if index != '*' else []
                },
                'page': {
                    'limit': 1000  # Max per request
                }
            }

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            for event in data.get('data', []):
                attributes = event.get('attributes', {})

                log_entry = LogEntry(
                    timestamp=datetime.fromtimestamp(
                        attributes.get('timestamp', 0) / 1000
                    ),
                    message=attributes.get('message', ''),
                    level=attributes.get('status', 'INFO').upper(),
                    source='datadog',
                    metadata={
                        'service': attributes.get('service'),
                        'host': attributes.get('host'),
                        'tags': attributes.get('tags', [])
                    }
                )
                logs.append(log_entry)

            logger.info(f"Fetched {len(logs)} logs from DataDog")
            return logs

        except RequestException as e:
            logger.error(f"Error fetching DataDog logs: {e}")
            return []

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch error logs specifically."""
        filters = filters or {}
        # Add error status filter
        filters['query'] = filters.get('query', '*') + ' status:(error OR critical OR fatal)'

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """Fetch performance metrics from DataDog."""
        metrics = []

        # Default metrics to fetch
        if not metric_names:
            metric_names = [
                'system.cpu.user',
                'system.mem.used',
                'system.load.1',
                'system.net.bytes_sent',
                'system.net.bytes_rcvd'
            ]

        try:
            from_ts = int(start_time.timestamp())
            to_ts = int(end_time.timestamp())

            url = f"https://api.{self.site}/api/v1/query"

            for metric_name in metric_names:
                params = {
                    'query': f'avg:{metric_name}',
                    'from': from_ts,
                    'to': to_ts
                }

                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()

                data = response.json()

                for series in data.get('series', []):
                    for point in series.get('pointlist', []):
                        timestamp_ms, value = point
                        metric = PerformanceMetric(
                            metric_name=metric_name,
                            value=value,
                            unit=series.get('unit', ''),
                            timestamp=datetime.fromtimestamp(timestamp_ms / 1000),
                            dimensions={'scope': series.get('scope', '')}
                        )
                        metrics.append(metric)

            logger.info(f"Fetched {len(metrics)} metrics from DataDog")
            return metrics

        except RequestException as e:
            logger.error(f"Error fetching DataDog metrics: {e}")
            return []
