"""
SLO Manager - Service Level Objectives and Error Budget Tracking

Implements symptom-based alerting instead of cause-based alerting.
Only alert when user experience is impacted (burning error budget).
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SLO:
    """Service Level Objective definition"""
    name: str
    service: str
    sli_type: str  # 'availability', 'latency', 'error_rate', 'throughput'
    target: float  # e.g., 99.9 for 99.9% availability
    window_days: int  # e.g., 30 for 30-day window
    measurement_query: str  # Prometheus query or metric path
    alert_threshold: float  # Percentage of budget consumed before alert


@dataclass
class ErrorBudget:
    """Error budget for an SLO"""
    slo_name: str
    total_budget: float  # Total allowed errors/downtime
    consumed: float  # Amount consumed
    remaining: float  # Amount remaining
    burn_rate: float  # Current rate of consumption
    exhaustion_date: Optional[str]  # Estimated date of budget exhaustion
    status: str  # 'healthy', 'warning', 'critical'


@dataclass
class Alert:
    """SLO-based alert"""
    alert_id: str
    slo_name: str
    severity: str  # 'warning', 'critical', 'page'
    message: str
    budget_consumed: float
    burn_rate: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None


class SLOManager:
    """
    Manages SLOs and error budgets for symptom-based alerting
    """

    def __init__(self, db_path: str = "data/slo_tracking.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.slos: Dict[str, SLO] = {}
        self._load_slos()

    def _init_database(self):
        """Initialize SQLite database for SLO tracking"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS slos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    service TEXT NOT NULL,
                    sli_type TEXT NOT NULL,
                    target REAL NOT NULL,
                    window_days INTEGER NOT NULL,
                    measurement_query TEXT NOT NULL,
                    alert_threshold REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sli_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slo_name TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    value REAL NOT NULL,
                    is_good BOOLEAN NOT NULL,
                    metadata TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    slo_name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    budget_consumed REAL NOT NULL,
                    burn_rate REAL NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_budget_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slo_name TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_budget REAL NOT NULL,
                    consumed REAL NOT NULL,
                    remaining REAL NOT NULL,
                    burn_rate REAL NOT NULL
                )
            """)

            conn.commit()

    def _load_slos(self):
        """Load SLOs from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM slos")
            for row in cursor.fetchall():
                slo = SLO(
                    name=row[1],
                    service=row[2],
                    sli_type=row[3],
                    target=row[4],
                    window_days=row[5],
                    measurement_query=row[6],
                    alert_threshold=row[7]
                )
                self.slos[slo.name] = slo
            logger.info(f"Loaded {len(self.slos)} SLOs")

    def create_slo(self, slo: SLO) -> bool:
        """
        Create a new SLO

        Args:
            slo: SLO object to create

        Returns:
            True if created successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO slos (name, service, sli_type, target, window_days,
                                     measurement_query, alert_threshold)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (slo.name, slo.service, slo.sli_type, slo.target,
                      slo.window_days, slo.measurement_query, slo.alert_threshold))
                conn.commit()

            self.slos[slo.name] = slo
            logger.info(f"Created SLO: {slo.name} for {slo.service}")
            return True

        except Exception as e:
            logger.error(f"Failed to create SLO: {e}")
            return False

    def record_measurement(self,
                          slo_name: str,
                          value: float,
                          is_good: bool,
                          metadata: Dict[str, Any] = None) -> bool:
        """
        Record an SLI measurement

        Args:
            slo_name: Name of SLO
            value: Measured value (e.g., response time, error count)
            is_good: Whether this measurement meets SLO target
            metadata: Additional context

        Returns:
            True if recorded successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO sli_measurements (slo_name, value, is_good, metadata)
                    VALUES (?, ?, ?, ?)
                """, (slo_name, value, is_good, json.dumps(metadata or {})))
                conn.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to record measurement: {e}")
            return False

    def calculate_error_budget(self, slo_name: str) -> Optional[ErrorBudget]:
        """
        Calculate current error budget for an SLO

        Args:
            slo_name: Name of SLO

        Returns:
            ErrorBudget object or None if SLO not found
        """
        slo = self.slos.get(slo_name)
        if not slo:
            logger.error(f"SLO not found: {slo_name}")
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get measurements within window
                since_date = datetime.now() - timedelta(days=slo.window_days)

                cursor = conn.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN is_good = 0 THEN 1 ELSE 0 END) as bad
                    FROM sli_measurements
                    WHERE slo_name = ? AND timestamp >= ?
                """, (slo_name, since_date))

                total, bad = cursor.fetchone()
                total = total or 0
                bad = bad or 0

                if total == 0:
                    return ErrorBudget(
                        slo_name=slo_name,
                        total_budget=100.0,
                        consumed=0.0,
                        remaining=100.0,
                        burn_rate=0.0,
                        exhaustion_date=None,
                        status='healthy'
                    )

                # Calculate actual vs target
                actual_success_rate = ((total - bad) / total) * 100
                target_success_rate = slo.target

                # Error budget = allowed failures
                allowed_failures = total * (1 - target_success_rate / 100)
                actual_failures = bad

                # Calculate budget consumption
                if allowed_failures > 0:
                    budget_consumed_pct = (actual_failures / allowed_failures) * 100
                else:
                    budget_consumed_pct = 100 if bad > 0 else 0

                remaining_pct = max(0, 100 - budget_consumed_pct)

                # Calculate burn rate (failures per day)
                cursor = conn.execute("""
                    SELECT COUNT(*)
                    FROM sli_measurements
                    WHERE slo_name = ? AND is_good = 0
                    AND timestamp >= datetime('now', '-1 day')
                """, (slo_name,))

                recent_failures = cursor.fetchone()[0]
                burn_rate = recent_failures  # Failures per day

                # Estimate exhaustion date
                if burn_rate > 0 and remaining_pct > 0:
                    days_until_exhaustion = (allowed_failures - actual_failures) / burn_rate
                    exhaustion_date = (datetime.now() + timedelta(days=days_until_exhaustion)).strftime('%Y-%m-%d')
                else:
                    exhaustion_date = None

                # Determine status
                if budget_consumed_pct >= slo.alert_threshold:
                    status = 'critical'
                elif budget_consumed_pct >= (slo.alert_threshold * 0.7):
                    status = 'warning'
                else:
                    status = 'healthy'

                error_budget = ErrorBudget(
                    slo_name=slo_name,
                    total_budget=allowed_failures,
                    consumed=actual_failures,
                    remaining=max(0, allowed_failures - actual_failures),
                    burn_rate=burn_rate,
                    exhaustion_date=exhaustion_date,
                    status=status
                )

                # Store in history
                conn.execute("""
                    INSERT INTO error_budget_history
                    (slo_name, date, total_budget, consumed, remaining, burn_rate)
                    VALUES (?, DATE('now'), ?, ?, ?, ?)
                """, (slo_name, error_budget.total_budget, error_budget.consumed,
                      error_budget.remaining, error_budget.burn_rate))
                conn.commit()

                return error_budget

        except Exception as e:
            logger.error(f"Failed to calculate error budget: {e}")
            return None

    def check_and_alert(self, slo_name: str) -> Optional[Alert]:
        """
        Check error budget and generate alert if threshold exceeded

        Args:
            slo_name: Name of SLO to check

        Returns:
            Alert object if threshold exceeded, None otherwise
        """
        slo = self.slos.get(slo_name)
        if not slo:
            return None

        error_budget = self.calculate_error_budget(slo_name)
        if not error_budget:
            return None

        # Only alert if burning error budget (symptom-based)
        if error_budget.status == 'healthy':
            return None

        # Determine severity based on burn rate
        if error_budget.burn_rate > (error_budget.total_budget / 7):  # Will exhaust in < 7 days
            severity = 'page'
            message = f"CRITICAL: {slo.service} is burning error budget rapidly. " \
                     f"Budget will exhaust in ~{(error_budget.remaining / error_budget.burn_rate):.1f} days. " \
                     f"Remaining: {error_budget.remaining:.0f} errors"
        elif error_budget.status == 'critical':
            severity = 'critical'
            message = f"Error budget exceeded for {slo.service}. " \
                     f"Consumed: {(error_budget.consumed/error_budget.total_budget)*100:.1f}%. " \
                     f"Remaining: {error_budget.remaining:.0f} errors"
        else:
            severity = 'warning'
            message = f"Error budget warning for {slo.service}. " \
                     f"Consumed: {(error_budget.consumed/error_budget.total_budget)*100:.1f}%"

        alert = Alert(
            alert_id=f"{slo_name}_{int(datetime.now().timestamp())}",
            slo_name=slo_name,
            severity=severity,
            message=message,
            budget_consumed=(error_budget.consumed / error_budget.total_budget) * 100,
            burn_rate=error_budget.burn_rate,
            triggered_at=datetime.now()
        )

        # Store alert
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO alerts
                    (alert_id, slo_name, severity, message, budget_consumed, burn_rate)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (alert.alert_id, alert.slo_name, alert.severity, alert.message,
                      alert.budget_consumed, alert.burn_rate))
                conn.commit()

            logger.warning(f"SLO alert triggered: {alert.message}")

        except Exception as e:
            logger.error(f"Failed to store alert: {e}")

        return alert

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Mark an alert as resolved

        Args:
            alert_id: ID of alert to resolve

        Returns:
            True if resolved successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE alerts
                    SET resolved_at = CURRENT_TIMESTAMP
                    WHERE alert_id = ?
                """, (alert_id,))
                conn.commit()

            logger.info(f"Alert resolved: {alert_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT alert_id, slo_name, severity, message, budget_consumed,
                           burn_rate, triggered_at
                    FROM alerts
                    WHERE resolved_at IS NULL
                    ORDER BY triggered_at DESC
                """)

                alerts = []
                for row in cursor.fetchall():
                    alert = Alert(
                        alert_id=row[0],
                        slo_name=row[1],
                        severity=row[2],
                        message=row[3],
                        budget_consumed=row[4],
                        burn_rate=row[5],
                        triggered_at=datetime.fromisoformat(row[6])
                    )
                    alerts.append(alert)

                return alerts

        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []

    def get_slo_report(self, slo_name: str) -> Dict[str, Any]:
        """
        Generate comprehensive SLO report

        Args:
            slo_name: Name of SLO

        Returns:
            Dictionary with SLO metrics and status
        """
        slo = self.slos.get(slo_name)
        if not slo:
            return {}

        error_budget = self.calculate_error_budget(slo_name)
        if not error_budget:
            return {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get recent measurements
                since_date = datetime.now() - timedelta(days=slo.window_days)
                cursor = conn.execute("""
                    SELECT DATE(timestamp) as date,
                           COUNT(*) as total,
                           SUM(CASE WHEN is_good = 1 THEN 1 ELSE 0 END) as good
                    FROM sli_measurements
                    WHERE slo_name = ? AND timestamp >= ?
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                """, (slo_name, since_date))

                daily_metrics = []
                for row in cursor.fetchall():
                    date, total, good = row
                    success_rate = (good / total * 100) if total > 0 else 0
                    daily_metrics.append({
                        'date': date,
                        'total': total,
                        'good': good,
                        'success_rate': success_rate,
                        'meets_target': success_rate >= slo.target
                    })

                return {
                    'slo': asdict(slo),
                    'error_budget': asdict(error_budget),
                    'daily_metrics': daily_metrics,
                    'report_generated_at': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to generate SLO report: {e}")
            return {}


# Predefined SLOs for common services
COMMON_SLOS = [
    SLO(
        name="api_availability",
        service="api",
        sli_type="availability",
        target=99.9,  # 99.9% uptime
        window_days=30,
        measurement_query="up{job='api'}",
        alert_threshold=80.0  # Alert when 80% of error budget consumed
    ),
    SLO(
        name="api_latency_p99",
        service="api",
        sli_type="latency",
        target=99.0,  # 99% of requests < 500ms
        window_days=30,
        measurement_query="histogram_quantile(0.99, http_request_duration_seconds_bucket)",
        alert_threshold=75.0
    ),
    SLO(
        name="api_error_rate",
        service="api",
        sli_type="error_rate",
        target=99.5,  # < 0.5% error rate
        window_days=7,
        measurement_query="rate(http_requests_total{status=~'5..'}[5m])",
        alert_threshold=85.0
    ),
    SLO(
        name="database_availability",
        service="database",
        sli_type="availability",
        target=99.95,  # 99.95% uptime
        window_days=30,
        measurement_query="up{job='postgres'}",
        alert_threshold=90.0
    )
]


def create_common_slos(manager: SLOManager):
    """Create predefined SLOs for common services"""
    for slo in COMMON_SLOS:
        manager.create_slo(slo)
    logger.info(f"Created {len(COMMON_SLOS)} common SLOs")
