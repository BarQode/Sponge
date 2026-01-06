"""Dynatrace integration for log and metrics collection."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import requests
from requests.exceptions import RequestException

from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class DynatraceIntegration(BaseIntegration):
    """Dynatrace integration."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_token = config.get('api_token')
        self.environment_url = config.get('environment_url')

        if not self.api_token or not self.environment_url:
            raise ValueError("Dynatrace API token and environment URL required")

        self.headers = {'Authorization': f'Api-Token {self.api_token}'}
        logger.info(f"Dynatrace integration initialized")

    def fetch_logs(self, start_time: datetime, end_time: datetime, filters: Optional[Dict[str, Any]] = None) -> List[LogEntry]:
        logs = []
        try:
            url = f"{self.environment_url}/api/v2/logs/search"
            payload = {
                "from": start_time.isoformat(),
                "to": end_time.isoformat(),
                "query": filters.get('query', '') if filters else ''
            }
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            for result in response.json().get('results', []):
                logs.append(LogEntry(
                    timestamp=datetime.fromisoformat(result.get('timestamp', start_time.isoformat())),
                    message=result.get('content', ''),
                    level=result.get('status', 'INFO').upper(),
                    source='dynatrace',
                    metadata=result
                ))
            logger.info(f"Fetched {len(logs)} logs from Dynatrace")
        except RequestException as e:
            logger.error(f"Error fetching Dynatrace logs: {e}")
        return logs

    def fetch_errors(self, start_time: datetime, end_time: datetime, filters: Optional[Dict[str, Any]] = None) -> List[LogEntry]:
        filters = filters or {}
        filters['query'] = filters.get('query', '') + ' status:"ERROR" OR status:"CRITICAL"'
        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(self, start_time: datetime, end_time: datetime, metric_names: Optional[List[str]] = None) -> List[PerformanceMetric]:
        metrics = []
        try:
            url = f"{self.environment_url}/api/v2/metrics/query"
            metric_names = metric_names or ['builtin:host.cpu.usage', 'builtin:host.mem.usage']

            for metric in metric_names:
                params = {
                    'metricSelector': metric,
                    'from': start_time.isoformat(),
                    'to': end_time.isoformat()
                }
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                response.raise_for_status()

                for result in response.json().get('result', []):
                    for datapoint in result.get('data', []):
                        metrics.append(PerformanceMetric(
                            metric_name=metric,
                            value=datapoint.get('values', [0])[0],
                            unit=result.get('unit', ''),
                            timestamp=datetime.fromtimestamp(datapoint['timestamps'][0] / 1000),
                            dimensions=result.get('dimensions', {})
                        ))
            logger.info(f"Fetched {len(metrics)} metrics from Dynatrace")
        except RequestException as e:
            logger.error(f"Error fetching Dynatrace metrics: {e}")
        return metrics
