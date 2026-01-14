"""
Prometheus Integration for Metrics and Monitoring

Exposes metrics for SRE automation, security operations, and ML training.
Provides exporters for Prometheus scraping.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from prometheus_client import Counter, Gauge, Histogram, Summary, Info, Enum
from prometheus_client import start_http_server, REGISTRY
import threading

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Prometheus metrics for Sponge RCA Tool

    Exposes comprehensive metrics for monitoring:
    - SRE automation (toil, runbooks, SLOs)
    - Security operations (incidents, access grants)
    - ML training (accuracy, latency)
    - System health (CPU, memory, disk)
    """

    def __init__(self, port: int = 9090):
        self.port = port
        self._init_metrics()
        self._server_thread = None

    def _init_metrics(self):
        """Initialize Prometheus metrics"""

        # === SRE Automation Metrics ===

        # Toil tracking
        self.toil_time_hours = Gauge(
            'sponge_toil_time_hours_total',
            'Total toil time in hours',
            ['category']
        )

        self.toil_tasks_total = Counter(
            'sponge_toil_tasks_total',
            'Total number of toil tasks tracked',
            ['category', 'automatable']
        )

        self.automated_tasks_total = Counter(
            'sponge_automated_tasks_total',
            'Total number of tasks automated',
            ['category']
        )

        self.toil_percentage = Gauge(
            'sponge_toil_percentage',
            'Percentage of time spent on toil'
        )

        # Runbook automation
        self.runbook_executions_total = Counter(
            'sponge_runbook_executions_total',
            'Total runbook executions',
            ['runbook_name', 'status']
        )

        self.runbook_execution_duration = Histogram(
            'sponge_runbook_execution_duration_seconds',
            'Runbook execution duration',
            ['runbook_name'],
            buckets=[1, 5, 10, 30, 60, 120, 300]
        )

        self.runbook_success_rate = Gauge(
            'sponge_runbook_success_rate',
            'Runbook success rate',
            ['runbook_name']
        )

        # SLO metrics
        self.slo_error_budget_remaining = Gauge(
            'sponge_slo_error_budget_remaining',
            'Remaining error budget percentage',
            ['slo_name']
        )

        self.slo_burn_rate = Gauge(
            'sponge_slo_burn_rate',
            'Current error budget burn rate',
            ['slo_name']
        )

        self.slo_alerts_total = Counter(
            'sponge_slo_alerts_total',
            'Total SLO alerts triggered',
            ['slo_name', 'severity']
        )

        self.slo_success_rate = Gauge(
            'sponge_slo_success_rate_percent',
            'Current SLO success rate percentage',
            ['slo_name']
        )

        # Self-healing
        self.self_healing_actions_total = Counter(
            'sponge_self_healing_actions_total',
            'Total self-healing actions taken',
            ['action_type', 'status']
        )

        self.self_healing_success_rate = Gauge(
            'sponge_self_healing_success_rate',
            'Self-healing success rate percentage'
        )

        # === Security Automation Metrics ===

        # JIT Access Control
        self.access_requests_total = Counter(
            'sponge_access_requests_total',
            'Total access requests',
            ['resource', 'status']
        )

        self.active_access_grants = Gauge(
            'sponge_active_access_grants',
            'Number of active access grants',
            ['resource']
        )

        self.access_grant_duration = Histogram(
            'sponge_access_grant_duration_minutes',
            'Access grant duration',
            ['resource'],
            buckets=[30, 60, 120, 240, 480]
        )

        # SOAR
        self.security_incidents_total = Counter(
            'sponge_security_incidents_total',
            'Total security incidents',
            ['incident_type', 'severity']
        )

        self.incidents_resolved_total = Counter(
            'sponge_incidents_resolved_total',
            'Total incidents resolved',
            ['incident_type', 'resolution_type']
        )

        self.incident_resolution_time = Histogram(
            'sponge_incident_resolution_time_seconds',
            'Time to resolve incidents',
            ['incident_type'],
            buckets=[60, 300, 900, 1800, 3600, 7200]
        )

        self.active_incidents = Gauge(
            'sponge_active_incidents',
            'Number of active security incidents',
            ['severity']
        )

        # Compliance
        self.compliance_violations_total = Counter(
            'sponge_compliance_violations_total',
            'Total compliance violations detected',
            ['standard', 'severity']
        )

        self.compliance_score = Gauge(
            'sponge_compliance_score',
            'Compliance score percentage',
            ['standard']
        )

        self.compliance_violations_active = Gauge(
            'sponge_compliance_violations_active',
            'Number of active compliance violations',
            ['standard', 'severity']
        )

        self.auto_remediated_violations = Counter(
            'sponge_auto_remediated_violations_total',
            'Total auto-remediated compliance violations',
            ['standard']
        )

        # Threat Intelligence
        self.threat_indicators_total = Gauge(
            'sponge_threat_indicators_total',
            'Total threat indicators in database',
            ['indicator_type']
        )

        self.threat_lookups_total = Counter(
            'sponge_threat_lookups_total',
            'Total threat intelligence lookups',
            ['lookup_type', 'result']
        )

        self.malicious_indicators_blocked = Counter(
            'sponge_malicious_indicators_blocked_total',
            'Total malicious indicators blocked',
            ['indicator_type']
        )

        # === ML Training Metrics ===

        self.ml_training_runs_total = Counter(
            'sponge_ml_training_runs_total',
            'Total ML training runs',
            ['model_type', 'status']
        )

        self.ml_training_duration = Histogram(
            'sponge_ml_training_duration_seconds',
            'ML training duration',
            ['model_type'],
            buckets=[60, 300, 600, 1800, 3600, 7200]
        )

        self.ml_model_accuracy = Gauge(
            'sponge_ml_model_accuracy',
            'ML model accuracy percentage',
            ['model_type']
        )

        self.ml_predictions_total = Counter(
            'sponge_ml_predictions_total',
            'Total ML predictions made',
            ['model_type', 'prediction']
        )

        self.ml_prediction_latency = Histogram(
            'sponge_ml_prediction_latency_seconds',
            'ML prediction latency',
            ['model_type'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
        )

        # === System Health Metrics ===

        self.system_cpu_usage = Gauge(
            'sponge_system_cpu_usage_percent',
            'System CPU usage percentage'
        )

        self.system_memory_usage = Gauge(
            'sponge_system_memory_usage_percent',
            'System memory usage percentage'
        )

        self.system_disk_usage = Gauge(
            'sponge_system_disk_usage_percent',
            'System disk usage percentage',
            ['mount_point']
        )

        self.knowledge_base_entries = Gauge(
            'sponge_knowledge_base_entries_total',
            'Total entries in knowledge base'
        )

        self.scraping_operations_total = Counter(
            'sponge_scraping_operations_total',
            'Total web scraping operations',
            ['source', 'status']
        )

        logger.info("Prometheus metrics initialized")

    def start_server(self):
        """Start Prometheus metrics HTTP server"""
        try:
            start_http_server(self.port)
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")

    def start_server_async(self):
        """Start Prometheus metrics server in background thread"""
        if self._server_thread and self._server_thread.is_alive():
            logger.warning("Prometheus server already running")
            return

        self._server_thread = threading.Thread(target=self.start_server, daemon=True)
        self._server_thread.start()
        logger.info("Prometheus metrics server started in background")

    # === SRE Metrics Methods ===

    def record_toil_task(self, category: str, time_hours: float, is_automatable: bool):
        """Record a toil task"""
        self.toil_time_hours.labels(category=category).inc(time_hours)
        self.toil_tasks_total.labels(
            category=category,
            automatable='yes' if is_automatable else 'no'
        ).inc()

    def record_automated_task(self, category: str):
        """Record an automated task"""
        self.automated_tasks_total.labels(category=category).inc()

    def update_toil_percentage(self, percentage: float):
        """Update toil percentage"""
        self.toil_percentage.set(percentage)

    def record_runbook_execution(self, runbook_name: str, duration: float, success: bool):
        """Record runbook execution"""
        status = 'success' if success else 'failed'
        self.runbook_executions_total.labels(
            runbook_name=runbook_name,
            status=status
        ).inc()
        self.runbook_execution_duration.labels(runbook_name=runbook_name).observe(duration)

    def update_runbook_success_rate(self, runbook_name: str, rate: float):
        """Update runbook success rate"""
        self.runbook_success_rate.labels(runbook_name=runbook_name).set(rate)

    def update_slo_metrics(self, slo_name: str, budget_remaining: float,
                          burn_rate: float, success_rate: float):
        """Update SLO metrics"""
        self.slo_error_budget_remaining.labels(slo_name=slo_name).set(budget_remaining)
        self.slo_burn_rate.labels(slo_name=slo_name).set(burn_rate)
        self.slo_success_rate.labels(slo_name=slo_name).set(success_rate)

    def record_slo_alert(self, slo_name: str, severity: str):
        """Record SLO alert"""
        self.slo_alerts_total.labels(slo_name=slo_name, severity=severity).inc()

    def record_self_healing_action(self, action_type: str, success: bool):
        """Record self-healing action"""
        status = 'success' if success else 'failed'
        self.self_healing_actions_total.labels(
            action_type=action_type,
            status=status
        ).inc()

    def update_self_healing_success_rate(self, rate: float):
        """Update self-healing success rate"""
        self.self_healing_success_rate.set(rate)

    # === Security Metrics Methods ===

    def record_access_request(self, resource: str, status: str):
        """Record access request"""
        self.access_requests_total.labels(resource=resource, status=status).inc()

    def update_active_access_grants(self, resource: str, count: int):
        """Update active access grants count"""
        self.active_access_grants.labels(resource=resource).set(count)

    def record_access_grant_duration(self, resource: str, duration_minutes: float):
        """Record access grant duration"""
        self.access_grant_duration.labels(resource=resource).observe(duration_minutes)

    def record_security_incident(self, incident_type: str, severity: str):
        """Record security incident"""
        self.security_incidents_total.labels(
            incident_type=incident_type,
            severity=severity
        ).inc()

    def record_incident_resolution(self, incident_type: str, resolution_type: str,
                                   duration_seconds: float):
        """Record incident resolution"""
        self.incidents_resolved_total.labels(
            incident_type=incident_type,
            resolution_type=resolution_type
        ).inc()
        self.incident_resolution_time.labels(incident_type=incident_type).observe(duration_seconds)

    def update_active_incidents(self, severity: str, count: int):
        """Update active incidents count"""
        self.active_incidents.labels(severity=severity).set(count)

    def record_compliance_violation(self, standard: str, severity: str):
        """Record compliance violation"""
        self.compliance_violations_total.labels(standard=standard, severity=severity).inc()

    def update_compliance_score(self, standard: str, score: float):
        """Update compliance score"""
        self.compliance_score.labels(standard=standard).set(score)

    def update_compliance_violations_active(self, standard: str, severity: str, count: int):
        """Update active compliance violations"""
        self.compliance_violations_active.labels(
            standard=standard,
            severity=severity
        ).set(count)

    def record_auto_remediated_violation(self, standard: str):
        """Record auto-remediated violation"""
        self.auto_remediated_violations.labels(standard=standard).inc()

    def update_threat_indicators(self, indicator_type: str, count: int):
        """Update threat indicators count"""
        self.threat_indicators_total.labels(indicator_type=indicator_type).set(count)

    def record_threat_lookup(self, lookup_type: str, is_malicious: bool):
        """Record threat intelligence lookup"""
        result = 'malicious' if is_malicious else 'clean'
        self.threat_lookups_total.labels(lookup_type=lookup_type, result=result).inc()

    def record_blocked_indicator(self, indicator_type: str):
        """Record blocked malicious indicator"""
        self.malicious_indicators_blocked.labels(indicator_type=indicator_type).inc()

    # === ML Metrics Methods ===

    def record_ml_training(self, model_type: str, duration: float, success: bool):
        """Record ML training run"""
        status = 'success' if success else 'failed'
        self.ml_training_runs_total.labels(model_type=model_type, status=status).inc()
        self.ml_training_duration.labels(model_type=model_type).observe(duration)

    def update_ml_model_accuracy(self, model_type: str, accuracy: float):
        """Update ML model accuracy"""
        self.ml_model_accuracy.labels(model_type=model_type).set(accuracy)

    def record_ml_prediction(self, model_type: str, prediction: str, latency: float):
        """Record ML prediction"""
        self.ml_predictions_total.labels(model_type=model_type, prediction=prediction).inc()
        self.ml_prediction_latency.labels(model_type=model_type).observe(latency)

    # === System Metrics Methods ===

    def update_system_metrics(self, cpu: float, memory: float, disk: Dict[str, float]):
        """Update system health metrics"""
        self.system_cpu_usage.set(cpu)
        self.system_memory_usage.set(memory)
        for mount_point, usage in disk.items():
            self.system_disk_usage.labels(mount_point=mount_point).set(usage)

    def update_knowledge_base_entries(self, count: int):
        """Update knowledge base entries count"""
        self.knowledge_base_entries.set(count)

    def record_scraping_operation(self, source: str, success: bool):
        """Record web scraping operation"""
        status = 'success' if success else 'failed'
        self.scraping_operations_total.labels(source=source, status=status).inc()


# Global metrics instance
metrics = PrometheusMetrics()


def get_metrics() -> PrometheusMetrics:
    """Get global Prometheus metrics instance"""
    return metrics
