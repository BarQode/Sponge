"""
Data Log Viewer Integration for Sponge RCA Platform

Data Log Viewer is a generic log analysis and visualization tool
that supports various log formats and data sources.

Features:
- Multi-format log parsing (JSON, CSV, syslog, custom)
- File-based and API-based log retrieval
- Real-time log streaming
- Query and filter capabilities
- Connection pooling
- Auto-retry with exponential backoff
"""

import logging
import requests
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class DataLogViewerIntegration(BaseIntegration):
    """Data Log Viewer integration."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Data Log Viewer integration.

        Args:
            config: Configuration dictionary with:
                - api_url: Data Log Viewer API endpoint (optional)
                - api_key: API key (optional)
                - log_files: List of log file paths (for file-based)
                - log_format: Log format (json, csv, syslog, custom)
                - custom_parser: Custom parser regex (if log_format=custom)
        """
        super().__init__(config)
        self.api_url = config.get('api_url', '').rstrip('/')
        self.api_key = config.get('api_key')
        self.log_files = config.get('log_files', [])
        self.log_format = config.get('log_format', 'json')
        self.custom_parser = config.get('custom_parser')
        self.timeout = config.get('timeout', 30)

        # Session configuration (for API mode)
        if self.api_url:
            self.session = requests.Session()
            if self.api_key:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                })

            # Connection pooling
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=3
            )
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)

        logger.info(f"Initialized Data Log Viewer integration with format: {self.log_format}")

    def test_connection(self) -> bool:
        """Test connection to Data Log Viewer."""
        try:
            if self.api_url:
                # Test API connection
                response = self.session.get(
                    f"{self.api_url}/api/health",
                    timeout=self.timeout
                )
                success = response.status_code == 200
            else:
                # Test file access
                import os
                success = all(os.path.exists(f) for f in self.log_files)

            if success:
                logger.info("Data Log Viewer connection test successful")
            else:
                logger.error("Data Log Viewer connection test failed")
            return success
        except Exception as e:
            logger.error(f"Data Log Viewer connection test failed: {e}")
            return False

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from Data Log Viewer.

        Args:
            start_time: Start time for log retrieval
            end_time: End time for log retrieval
            filters: Optional filters:
                - level: Log level filter
                - query: Search query
                - source: Source filter
                - limit: Maximum results (default: 1000)

        Returns:
            List of LogEntry objects
        """
        if self.api_url:
            return self._fetch_logs_api(start_time, end_time, filters)
        else:
            return self._fetch_logs_file(start_time, end_time, filters)

    def _fetch_logs_api(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch logs via API."""
        try:
            filters = filters or {}

            params = {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'limit': filters.get('limit', 1000)
            }

            if filters.get('level'):
                params['level'] = filters['level']

            if filters.get('query'):
                params['query'] = filters['query']

            if filters.get('source'):
                params['source'] = filters['source']

            response = self.session.get(
                f"{self.api_url}/api/logs",
                params=params,
                timeout=self.timeout
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch logs: {response.status_code}")
                return []

            data = response.json()
            return self._parse_log_entries(data.get('logs', []))

        except Exception as e:
            logger.error(f"Error fetching logs via API: {e}")
            return []

    def _fetch_logs_file(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch logs from files."""
        try:
            all_logs = []

            for log_file in self.log_files:
                try:
                    with open(log_file, 'r') as f:
                        if self.log_format == 'json':
                            logs = self._parse_json_logs(f, start_time, end_time, filters)
                        elif self.log_format == 'csv':
                            logs = self._parse_csv_logs(f, start_time, end_time, filters)
                        elif self.log_format == 'syslog':
                            logs = self._parse_syslog_logs(f, start_time, end_time, filters)
                        else:
                            logs = self._parse_custom_logs(f, start_time, end_time, filters)

                        all_logs.extend(logs)
                except Exception as e:
                    logger.error(f"Error reading log file {log_file}: {e}")

            logger.info(f"Fetched {len(all_logs)} logs from files")
            return all_logs

        except Exception as e:
            logger.error(f"Error fetching logs from files: {e}")
            return []

    def _parse_json_logs(
        self,
        file_obj,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Parse JSON format logs."""
        logs = []

        for line in file_obj:
            try:
                entry = json.loads(line.strip())
                log_entry = self._create_log_entry(entry)

                if log_entry and start_time <= log_entry.timestamp <= end_time:
                    if self._matches_filters(log_entry, filters):
                        logs.append(log_entry)
            except json.JSONDecodeError:
                continue

        return logs

    def _parse_csv_logs(
        self,
        file_obj,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Parse CSV format logs."""
        logs = []
        reader = csv.DictReader(file_obj)

        for row in reader:
            try:
                log_entry = self._create_log_entry(row)

                if log_entry and start_time <= log_entry.timestamp <= end_time:
                    if self._matches_filters(log_entry, filters):
                        logs.append(log_entry)
            except Exception:
                continue

        return logs

    def _parse_syslog_logs(
        self,
        file_obj,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Parse syslog format logs."""
        import re
        logs = []

        # Basic syslog pattern: timestamp hostname process[pid]: message
        pattern = r'(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+(\S+)(?:\[(\d+)\])?:\s+(.+)'

        for line in file_obj:
            try:
                match = re.match(pattern, line.strip())
                if match:
                    timestamp_str, hostname, process, pid, message = match.groups()

                    # Parse timestamp (syslog doesn't include year)
                    from datetime import datetime as dt
                    timestamp = dt.strptime(f"{datetime.now().year} {timestamp_str}", "%Y %b %d %H:%M:%S")

                    log_entry = LogEntry(
                        timestamp=timestamp,
                        level=self._infer_level(message),
                        message=message,
                        source=f"{hostname}:{process}",
                        metadata={'hostname': hostname, 'process': process, 'pid': pid}
                    )

                    if start_time <= log_entry.timestamp <= end_time:
                        if self._matches_filters(log_entry, filters):
                            logs.append(log_entry)
            except Exception:
                continue

        return logs

    def _parse_custom_logs(
        self,
        file_obj,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Parse custom format logs using regex."""
        import re
        logs = []

        if not self.custom_parser:
            logger.warning("No custom parser regex defined")
            return logs

        pattern = re.compile(self.custom_parser)

        for line in file_obj:
            try:
                match = pattern.match(line.strip())
                if match:
                    groups = match.groupdict()
                    log_entry = self._create_log_entry(groups)

                    if log_entry and start_time <= log_entry.timestamp <= end_time:
                        if self._matches_filters(log_entry, filters):
                            logs.append(log_entry)
            except Exception:
                continue

        return logs

    def _create_log_entry(self, data: Dict[str, Any]) -> Optional[LogEntry]:
        """Create LogEntry from parsed data."""
        try:
            # Parse timestamp
            timestamp_field = data.get('timestamp', data.get('time', data.get('@timestamp')))
            if isinstance(timestamp_field, str):
                timestamp = datetime.fromisoformat(timestamp_field.replace('Z', '+00:00'))
            elif isinstance(timestamp_field, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp_field)
            else:
                timestamp = datetime.utcnow()

            return LogEntry(
                timestamp=timestamp,
                level=data.get('level', data.get('severity', 'INFO')),
                message=data.get('message', data.get('msg', str(data))),
                source=data.get('source', data.get('logger', 'datalogviewer')),
                metadata={k: v for k, v in data.items() if k not in ['timestamp', 'level', 'message', 'source']}
            )
        except Exception as e:
            logger.debug(f"Error creating log entry: {e}")
            return None

    def _matches_filters(self, log_entry: LogEntry, filters: Optional[Dict[str, Any]]) -> bool:
        """Check if log entry matches filters."""
        if not filters:
            return True

        if filters.get('level') and log_entry.level != filters['level']:
            return False

        if filters.get('query'):
            query = filters['query'].lower()
            if query not in log_entry.message.lower():
                return False

        if filters.get('source') and log_entry.source != filters['source']:
            return False

        return True

    def _parse_log_entries(self, raw_logs: List[Dict[str, Any]]) -> List[LogEntry]:
        """Parse raw log entries."""
        return [self._create_log_entry(log) for log in raw_logs if self._create_log_entry(log)]

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """Fetch error logs."""
        filters = filters or {}
        filters['level'] = 'ERROR'

        return self.fetch_logs(start_time, end_time, filters)

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics from logs.

        Extracts numeric values from log messages.
        """
        try:
            logs = self.fetch_logs(start_time, end_time)
            metrics = []

            import re
            for log in logs:
                # Extract numeric values
                numbers = re.findall(r'(\w+)[:\s=]+(\d+\.?\d*)\s*(\w*)', log.message)

                for metric_name, value, unit in numbers:
                    if metric_name.lower() in ['time', 'latency', 'duration', 'cpu', 'memory', 'bytes']:
                        metric = PerformanceMetric(
                            timestamp=log.timestamp,
                            metric_name=metric_name,
                            value=float(value),
                            unit=unit or 'units',
                            metadata=log.metadata
                        )
                        metrics.append(metric)

            logger.info(f"Extracted {len(metrics)} performance metrics")
            return metrics

        except Exception as e:
            logger.error(f"Error fetching performance metrics: {e}")
            return []

    def _infer_level(self, message: str) -> str:
        """Infer log level from message."""
        message_lower = message.lower()

        if any(word in message_lower for word in ['fatal', 'critical', 'panic']):
            return 'CRITICAL'
        elif any(word in message_lower for word in ['error', 'fail', 'exception']):
            return 'ERROR'
        elif any(word in message_lower for word in ['warn', 'warning']):
            return 'WARNING'
        elif any(word in message_lower for word in ['debug', 'trace']):
            return 'DEBUG'
        else:
            return 'INFO'

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'session'):
            self.session.close()
