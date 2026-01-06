"""
Zombie Process Detector - Identifies defunct processes and orphaned resources.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from collections import defaultdict

from src.integrations.base import LogEntry

logger = logging.getLogger(__name__)


class ZombieDetection:
    """Result of zombie process detection."""

    def __init__(
        self,
        zombie_type: str,
        severity: str,
        description: str,
        affected_resources: List[str],
        indicators: Dict[str, Any],
        recommendations: List[str]
    ):
        self.zombie_type = zombie_type
        self.severity = severity
        self.description = description
        self.affected_resources = affected_resources
        self.indicators = indicators
        self.recommendations = recommendations
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'zombie_type': self.zombie_type,
            'severity': self.severity,
            'description': self.description,
            'affected_resources': self.affected_resources,
            'indicators': self.indicators,
            'recommendations': self.recommendations,
            'timestamp': self.timestamp.isoformat()
        }


class ZombieDetector:
    """
    Detects zombie processes and orphaned resources:
    - Defunct processes (classic zombies)
    - Orphaned file handles
    - Abandoned database connections
    - Stuck threads
    - Orphaned temporary files
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Zombie detector."""
        self.config = config or {}
        logger.info("Zombie Detector initialized")

    def analyze(self, logs: List[LogEntry]) -> List[ZombieDetection]:
        """Analyze logs to detect zombie processes and resources."""
        detections = []

        if not logs:
            return detections

        # Detect various zombie indicators
        detections.extend(self._detect_defunct_processes(logs))
        detections.extend(self._detect_orphaned_connections(logs))
        detections.extend(self._detect_file_handle_leaks(logs))
        detections.extend(self._detect_stuck_threads(logs))

        logger.info(f"Zombie Detection complete: found {len(detections)} issues")
        return detections

    def _detect_defunct_processes(self, logs: List[LogEntry]) -> List[ZombieDetection]:
        """Detect defunct/zombie processes from logs."""
        detections = []
        zombie_keywords = ['defunct', 'zombie process', '<defunct>', 'orphaned process']

        for log in logs:
            if any(keyword in log.message.lower() for keyword in zombie_keywords):
                detections.append(ZombieDetection(
                    zombie_type='defunct_process',
                    severity='medium',
                    description=f'Defunct process detected: {log.message[:150]}',
                    affected_resources=[log.source],
                    indicators={'log_message': log.message},
                    recommendations=[
                        'Identify parent process not reaping child processes',
                        'Review process spawning and cleanup code',
                        'Implement proper signal handling (SIGCHLD)',
                        'Use waitpid() or equivalent to clean up child processes',
                        'Check for background worker processes not being monitored',
                        'Restart affected services to clear zombie processes'
                    ]
                ))

        return detections

    def _detect_orphaned_connections(self, logs: List[LogEntry]) -> List[ZombieDetection]:
        """Detect orphaned database or network connections."""
        detections = []
        connection_keywords = [
            'connection pool exhausted',
            'too many connections',
            'connection leak',
            'unclosed connection',
            'connection not returned to pool'
        ]

        for log in logs:
            if any(keyword in log.message.lower() for keyword in connection_keywords):
                detections.append(ZombieDetection(
                    zombie_type='orphaned_connections',
                    severity='high',
                    description=f'Orphaned connections detected: {log.message[:150]}',
                    affected_resources=[log.source],
                    indicators={'log_message': log.message},
                    recommendations=[
                        'Review code for proper connection cleanup (try-finally blocks)',
                        'Implement connection timeout settings',
                        'Use connection pooling with proper size limits',
                        'Enable connection leak detection in pool configuration',
                        'Review database connection lifecycle',
                        'Check for long-running transactions holding connections',
                        'Implement automatic connection cleanup on timeout'
                    ]
                ))

        return detections

    def _detect_file_handle_leaks(self, logs: List[LogEntry]) -> List[ZombieDetection]:
        """Detect file handle leaks."""
        detections = []
        file_keywords = [
            'too many open files',
            'file descriptor leak',
            'cannot open file',
            'file handle exhausted'
        ]

        for log in logs:
            if any(keyword in log.message.lower() for keyword in file_keywords):
                detections.append(ZombieDetection(
                    zombie_type='file_handle_leak',
                    severity='high',
                    description=f'File handle leak detected: {log.message[:150]}',
                    affected_resources=[log.source],
                    indicators={'log_message': log.message},
                    recommendations=[
                        'Review code for unclosed file handles',
                        'Use context managers (with statements) for file operations',
                        'Check for leaked network sockets',
                        'Review logging configuration for file handle usage',
                        'Increase system file descriptor limits if legitimate usage',
                        'Implement file handle monitoring and alerts',
                        'Check for orphaned temporary files'
                    ]
                ))

        return detections

    def _detect_stuck_threads(self, logs: List[LogEntry]) -> List[ZombieDetection]:
        """Detect stuck or blocked threads."""
        detections = []
        thread_keywords = [
            'thread blocked',
            'deadlock detected',
            'thread stuck',
            'waiting for lock',
            'thread dump',
            'thread contention'
        ]

        for log in logs:
            if any(keyword in log.message.lower() for keyword in thread_keywords):
                detections.append(ZombieDetection(
                    zombie_type='stuck_threads',
                    severity='high',
                    description=f'Stuck threads detected: {log.message[:150]}',
                    affected_resources=[log.source],
                    indicators={'log_message': log.message},
                    recommendations=[
                        'Analyze thread dumps to identify blocking threads',
                        'Review lock acquisition order to prevent deadlocks',
                        'Implement lock timeout mechanisms',
                        'Use concurrent data structures to reduce contention',
                        'Review synchronization blocks for unnecessary locking',
                        'Consider using lock-free algorithms where appropriate',
                        'Implement thread pool monitoring and health checks'
                    ]
                ))

        return detections
