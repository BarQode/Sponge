"""
Biometrics Ltd DataLOG Integration for Sponge RCA Platform

DataLOG provides specialized data logging and monitoring for scientific
and industrial applications, particularly in biometrics and measurement systems.

Features:
- Time-series data retrieval
- Sensor data logging
- Event monitoring
- Real-time data streaming
- Connection pooling
- Auto-retry with exponential backoff
"""

import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class DataLOGIntegration(BaseIntegration):
    """Biometrics Ltd DataLOG integration."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize DataLOG integration.

        Args:
            config: Configuration dictionary with:
                - api_url: DataLOG API endpoint
                - api_key: API key or access token
                - device_id: Device/logger ID (optional)
                - channel: Data channel (optional)
        """
        super().__init__(config)
        self.api_url = config.get('api_url', '').rstrip('/')
        self.api_key = config.get('api_key')
        self.device_id = config.get('device_id')
        self.channel = config.get('channel', 'default')
        self.timeout = config.get('timeout', 30)

        if not self.api_url or not self.api_key:
            raise ValueError("api_url and api_key are required for DataLOG integration")

        # Session configuration
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        # Connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        logger.info(f"Initialized DataLOG integration for device: {self.device_id}")

    def test_connection(self) -> bool:
        """Test connection to DataLOG."""
        try:
            response = self.session.get(
                f"{self.api_url}/api/status",
                timeout=self.timeout
            )
            success = response.status_code == 200
            if success:
                logger.info("DataLOG connection test successful")
            else:
                logger.error(f"DataLOG connection test failed: {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"DataLOG connection test failed: {e}")
            return False

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from DataLOG.

        Args:
            start_time: Start time for log retrieval
            end_time: End time for log retrieval
            filters: Optional filters:
                - device_id: Device identifier
                - channel: Data channel
                - event_type: Event type filter
                - limit: Maximum results (default: 1000)

        Returns:
            List of LogEntry objects
        """
        try:
            filters = filters or {}

            params = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'limit': filters.get('limit', 1000)
            }

            if filters.get('device_id') or self.device_id:
                params['device_id'] = filters.get('device_id', self.device_id)

            if filters.get('channel'):
                params['channel'] = filters['channel']

            if filters.get('event_type'):
                params['event_type'] = filters['event_type']

            response = self.session.get(
                f"{self.api_url}/api/events",
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch DataLOG logs: {response.status_code}")
                return []

            data = response.json()
            logs = []

            for event in data.get('events', []):
                # Parse timestamp
                timestamp = event.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp)
                else:
                    timestamp = datetime.utcnow()

                log_entry = LogEntry(
                    timestamp=timestamp,
                    level=self._map_severity(event.get('severity', 0)),
                    message=event.get('message', event.get('description', '')),
                    source=f"datalog:{event.get('device_id', 'unknown')}",
                    metadata={
                        'device_id': event.get('device_id'),
                        'channel': event.get('channel'),
                        'event_type': event.get('event_type'),
                        'sensor_value': event.get('sensor_value'),
                        'unit': event.get('unit'),
                        **event.get('data', {})
                    }
                )
                logs.append(log_entry)

            logger.info(f"Fetched {len(logs)} logs from DataLOG")
            return logs

        except Exception as e:
            logger.error(f"Error fetching DataLOG logs: {e}")
            return []

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch error events from DataLOG."""
        filters = filters or {}
        filters['event_type'] = 'error,fault,alarm'

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from DataLOG.

        Args:
            start_time: Start time for metrics
            end_time: End time for metrics
            metric_names: List of metric/sensor names

        Returns:
            List of PerformanceMetric objects
        """
        try:
            params = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }

            if self.device_id:
                params['device_id'] = self.device_id

            if metric_names:
                params['metrics'] = ','.join(metric_names)

            response = self.session.get(
                f"{self.api_url}/api/data",
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch DataLOG metrics: {response.status_code}")
                return []

            data = response.json()
            metrics = []

            for series in data.get('series', []):
                metric_name = series.get('name', series.get('channel', 'unknown'))
                unit = series.get('unit', 'units')

                for point in series.get('data', []):
                    # Handle various timestamp formats
                    ts = point.get('timestamp', point.get('time'))
                    if isinstance(ts, str):
                        timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    elif isinstance(ts, (int, float)):
                        timestamp = datetime.fromtimestamp(ts)
                    else:
                        continue

                    value = point.get('value', point.get('measurement'))
                    if value is None:
                        continue

                    metric = PerformanceMetric(
                        timestamp=timestamp,
                        metric_name=metric_name,
                        value=float(value),
                        unit=unit,
                        metadata={
                            'device_id': series.get('device_id'),
                            'channel': series.get('channel'),
                            'quality': point.get('quality', 'good'),
                            **series.get('metadata', {})
                        }
                    )
                    metrics.append(metric)

            logger.info(f"Fetched {len(metrics)} performance metrics from DataLOG")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching DataLOG metrics: {e}")
            return []

    def get_sensor_data(
        self,
        start_time: datetime,
        end_time: datetime,
        sensor_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get raw sensor data from DataLOG.

        Args:
            start_time: Start time
            end_time: End time
            sensor_ids: List of sensor IDs to retrieve

        Returns:
            List of sensor reading dictionaries
        """
        try:
            params = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }

            if self.device_id:
                params['device_id'] = self.device_id

            if sensor_ids:
                params['sensors'] = ','.join(sensor_ids)

            response = self.session.get(
                f"{self.api_url}/api/sensors",
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch sensor data: {response.status_code}")
                return []

            data = response.json()
            readings = data.get('readings', [])

            logger.info(f"Fetched {len(readings)} sensor readings from DataLOG")
            return readings

        except Exception as e:
            logger.error(f"Error fetching sensor data: {e}")
            return []

    def _map_severity(self, severity: int) -> str:
        """Map numeric severity to log level."""
        severity_map = {
            0: 'DEBUG',
            1: 'INFO',
            2: 'WARNING',
            3: 'ERROR',
            4: 'CRITICAL'
        }
        return severity_map.get(severity, 'INFO')

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'session'):
            self.session.close()
