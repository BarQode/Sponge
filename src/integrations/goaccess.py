"""
GoAccess Integration for Web Server Log Analysis.

Parses and analyzes web server logs (Apache, Nginx, etc.) using GoAccess.
Provides real-time web analytics and log parsing.
"""

import logging
import subprocess
import json
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

logger = logging.getLogger(__name__)


class GoAccessIntegration(BaseIntegration):
    """
    Integration with GoAccess for web server log analysis.

    Features:
    - Apache/Nginx log parsing
    - Real-time analytics
    - JSON output for programmatic access
    - Custom log format support
    - Performance metrics extraction

    Note: Requires GoAccess binary to be installed on the system.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GoAccess integration.

        Args:
            config: Configuration dict with:
                - log_files: List of log file paths
                - log_format: Log format (COMBINED, COMMON, CLOUDFRONT, etc.)
                - goaccess_path: Path to goaccess binary (default: 'goaccess')
                - time_format: Time format string
                - date_format: Date format string
        """
        super().__init__(config)
        self.log_files = config.get('log_files', [])
        self.log_format = config.get('log_format', 'COMBINED')
        self.goaccess_path = config.get('goaccess_path', 'goaccess')
        self.time_format = config.get('time_format', '%H:%M:%S')
        self.date_format = config.get('date_format', '%d/%b/%Y')

        # Verify GoAccess is installed
        self._verify_goaccess()

        logger.info("GoAccess integration initialized")

    def _verify_goaccess(self):
        """Verify GoAccess is installed and accessible."""
        try:
            result = subprocess.run(
                [self.goaccess_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"GoAccess found: {result.stdout.strip()}")
            else:
                logger.warning("GoAccess not found - install with: apt-get install goaccess")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"GoAccess not available: {e}")

    def _parse_logs_with_goaccess(
        self,
        log_file: str,
        output_format: str = 'json'
    ) -> Optional[Dict[str, Any]]:
        """
        Parse log file using GoAccess.

        Args:
            log_file: Path to log file
            output_format: Output format (json, csv, html)

        Returns:
            Parsed log data as dictionary
        """
        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{output_format}', delete=False) as tmp_file:
            output_file = tmp_file.name

        try:
            cmd = [
                self.goaccess_path,
                log_file,
                '--log-format', self.log_format,
                '--date-format', self.date_format,
                '--time-format', self.time_format,
                '--output', output_file
            ]

            if output_format == 'json':
                cmd.append('--output-format=json')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                logger.error(f"GoAccess parsing failed: {result.stderr}")
                return None

            # Read output
            with open(output_file, 'r') as f:
                if output_format == 'json':
                    return json.load(f)
                else:
                    return {'raw': f.read()}

        except (subprocess.SubprocessError, json.JSONDecodeError, IOError) as e:
            logger.error(f"Error parsing logs with GoAccess: {e}")
            return None

        finally:
            # Clean up temporary file
            try:
                Path(output_file).unlink()
            except:
                pass

    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch and parse web server logs.

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters (status_code, method, etc.)

        Returns:
            List of LogEntry objects
        """
        logs = []

        for log_file in self.log_files:
            try:
                # Parse with GoAccess
                parsed_data = self._parse_logs_with_goaccess(log_file)

                if not parsed_data:
                    continue

                # Extract individual requests
                visitors = parsed_data.get('visitors', {}).get('data', [])

                for visitor in visitors:
                    hits = visitor.get('hits', {}).get('data', [])

                    for hit in hits:
                        # Parse timestamp
                        try:
                            timestamp = datetime.strptime(
                                hit.get('date', ''),
                                '%Y-%m-%d %H:%M:%S'
                            )

                            # Filter by time range
                            if timestamp < start_time or timestamp > end_time:
                                continue

                        except ValueError:
                            timestamp = datetime.utcnow()

                        # Determine log level based on status code
                        status_code = int(hit.get('status', {}).get('code', 200))
                        level = self._status_to_level(status_code)

                        # Apply filters
                        if filters:
                            if 'status_code' in filters and status_code != filters['status_code']:
                                continue
                            if 'method' in filters and hit.get('method') != filters['method']:
                                continue

                        log = LogEntry(
                            timestamp=timestamp,
                            message=f"{hit.get('method', 'GET')} {hit.get('req', '/')} - {status_code}",
                            level=level,
                            source='goaccess',
                            metadata={
                                'method': hit.get('method'),
                                'request': hit.get('req'),
                                'status_code': status_code,
                                'response_time': hit.get('time_served'),
                                'bytes_sent': hit.get('bytes_sent'),
                                'protocol': hit.get('protocol'),
                                'visitor_ip': visitor.get('data', {}).get('ip')
                            }
                        )
                        logs.append(log)

            except Exception as e:
                logger.error(f"Error processing log file {log_file}: {e}")

        logger.info(f"Fetched {len(logs)} web server logs via GoAccess")
        return logs

    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error logs (4xx, 5xx responses).

        Args:
            start_time: Start of time range
            end_time: End of time range
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        all_logs = self.fetch_logs(start_time, end_time, filters)
        return [log for log in all_logs if log.level in ['ERROR', 'CRITICAL', 'WARNING']]

    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Extract performance metrics from web logs.

        Args:
            start_time: Start of time range
            end_time: End of time range
            metric_names: Specific metrics to extract

        Returns:
            List of PerformanceMetric objects
        """
        metrics = []

        for log_file in self.log_files:
            parsed_data = self._parse_logs_with_goaccess(log_file)

            if not parsed_data:
                continue

            # Extract overall metrics
            general = parsed_data.get('general', {})

            metrics.append(PerformanceMetric(
                metric_name='total_requests',
                value=float(general.get('total_requests', 0)),
                unit='count',
                timestamp=datetime.utcnow(),
                dimensions={'log_file': log_file}
            ))

            metrics.append(PerformanceMetric(
                metric_name='unique_visitors',
                value=float(general.get('unique_visitors', 0)),
                unit='count',
                timestamp=datetime.utcnow(),
                dimensions={'log_file': log_file}
            ))

            metrics.append(PerformanceMetric(
                metric_name='failed_requests',
                value=float(general.get('failed_requests', 0)),
                unit='count',
                timestamp=datetime.utcnow(),
                dimensions={'log_file': log_file}
            ))

        return metrics

    def _status_to_level(self, status_code: int) -> str:
        """Convert HTTP status code to log level."""
        if status_code >= 500:
            return 'CRITICAL'
        elif status_code >= 400:
            return 'ERROR'
        elif status_code >= 300:
            return 'WARNING'
        else:
            return 'INFO'

    def test_connection(self) -> bool:
        """Test GoAccess availability and log file access."""
        try:
            # Check if log files exist
            for log_file in self.log_files:
                if not Path(log_file).exists():
                    logger.warning(f"Log file not found: {log_file}")
                    return False

            logger.info("GoAccess connection test: SUCCESS")
            return True

        except Exception as e:
            logger.error(f"GoAccess connection test FAILED: {e}")
            return False
