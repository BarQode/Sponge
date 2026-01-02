"""
Base integration class for all monitoring platform integrations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LogEntry:
    """Standardized log entry across all platforms."""

    def __init__(
        self,
        timestamp: datetime,
        message: str,
        level: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None
    ):
        self.timestamp = timestamp
        self.message = message
        self.level = level.upper()
        self.source = source
        self.metadata = metadata or {}
        self.metrics = metrics or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'level': self.level,
            'source': self.source,
            'metadata': self.metadata,
            'metrics': self.metrics
        }

    def __repr__(self) -> str:
        return f"LogEntry(timestamp={self.timestamp}, level={self.level}, source={self.source})"


class PerformanceMetric:
    """Standardized performance metric across all platforms."""

    def __init__(
        self,
        metric_name: str,
        value: float,
        unit: str,
        timestamp: datetime,
        dimensions: Optional[Dict[str, str]] = None
    ):
        self.metric_name = metric_name
        self.value = value
        self.unit = unit
        self.timestamp = timestamp
        self.dimensions = dimensions or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'metric_name': self.metric_name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'dimensions': self.dimensions
        }


class BaseIntegration(ABC):
    """
    Abstract base class for all monitoring platform integrations.

    All integrations must implement methods to fetch:
    - Logs
    - Error events
    - Performance metrics
    - Resource utilization data
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the integration.

        Args:
            config: Configuration dictionary with API keys and settings
        """
        self.config = config
        self.platform_name = self.__class__.__name__.replace('Integration', '')
        logger.info(f"Initializing {self.platform_name} integration")

    @abstractmethod
    def fetch_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch logs from the monitoring platform.

        Args:
            start_time: Start time for log retrieval
            end_time: End time for log retrieval
            filters: Optional filters (service name, log level, etc.)

        Returns:
            List of LogEntry objects
        """
        pass

    @abstractmethod
    def fetch_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Fetch error events specifically.

        Args:
            start_time: Start time for error retrieval
            end_time: End time for error retrieval
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        pass

    @abstractmethod
    def fetch_performance_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_names: Optional[List[str]] = None
    ) -> List[PerformanceMetric]:
        """
        Fetch performance metrics (CPU, memory, latency, etc.).

        Args:
            start_time: Start time for metrics
            end_time: End time for metrics
            metric_names: Specific metrics to fetch (None = all)

        Returns:
            List of PerformanceMetric objects
        """
        pass

    def fetch_recent_logs(
        self,
        hours: int = 24,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Convenience method to fetch logs from the last N hours.

        Args:
            hours: Number of hours to look back
            filters: Optional filters

        Returns:
            List of LogEntry objects
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        return self.fetch_logs(start_time, end_time, filters)

    def fetch_recent_errors(
        self,
        hours: int = 24,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[LogEntry]:
        """
        Convenience method to fetch errors from the last N hours.

        Args:
            hours: Number of hours to look back
            filters: Optional filters

        Returns:
            List of error LogEntry objects
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        return self.fetch_errors(start_time, end_time, filters)

    def test_connection(self) -> bool:
        """
        Test the connection to the monitoring platform.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch a small amount of recent data
            logs = self.fetch_recent_logs(hours=1)
            logger.info(f"{self.platform_name} connection test: SUCCESS")
            return True
        except Exception as e:
            logger.error(f"{self.platform_name} connection test FAILED: {e}")
            return False

    def get_platform_info(self) -> Dict[str, str]:
        """
        Get information about this integration.

        Returns:
            Dictionary with platform name and configuration info
        """
        return {
            'platform': self.platform_name,
            'configured': bool(self.config),
            'connection_tested': False  # Override in subclasses if desired
        }
