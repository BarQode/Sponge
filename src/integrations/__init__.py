"""
Integration modules for monitoring platforms.

Comprehensive support for 24+ log and monitoring platforms including:
- Cloud: AWS CloudWatch, Azure Monitor, GCP
- APM: DataDog, Dynatrace, New Relic, VelocityAP
- SIEM: Splunk, SolarWinds LEM
- Logs: ELK Stack, Grafana/Loki, Fluentd, Logstash
- SaaS: Sumo Logic, Loggly, Papertrail, Retrace, Logentries
- Metrics: Prometheus, Grafana
- Security: Sentry, Huntress, Coralogix
- Web Analytics: GoAccess
- Specialized: Biometrics DataLOG, Data Log Viewer
"""

from src.integrations.base import BaseIntegration, LogEntry, PerformanceMetric

# Cloud Platform Integrations
from src.integrations.aws_cloudwatch import CloudWatchIntegration
from src.integrations.azure_monitor import AzureMonitorIntegration

# APM & Monitoring Platforms
from src.integrations.datadog import DataDogIntegration
from src.integrations.dynatrace import DynatraceIntegration

# SIEM & Security
from src.integrations.splunk import SplunkIntegration
from src.integrations.solarwinds import SolarWindsIntegration
from src.integrations.sentry import SentryIntegration
from src.integrations.huntress import HuntressIntegration

# Elastic Stack
from src.integrations.elastic import ElasticIntegration
from src.integrations.logstash import LogstashIntegration

# Metrics & Visualization
from src.integrations.prometheus import PrometheusIntegration
from src.integrations.grafana import GrafanaIntegration

# Log Aggregation SaaS
from src.integrations.sumologic import SumoLogicIntegration
from src.integrations.loggly import LogglyIntegration
from src.integrations.papertrail import PapertrailIntegration
from src.integrations.coralogix import CoralogixIntegration
from src.integrations.lumigo import LumigoIntegration

# Log Collection & Processing
from src.integrations.fluentd import FluentdIntegration

# Application Performance
from src.integrations.retrace import RetraceIntegration

# Web Analytics
from src.integrations.goaccess import GoAccessIntegration

# Additional Platform Integrations
from src.integrations.logentries import LogentriesIntegration
from src.integrations.velocityap import VelocityAPIntegration
from src.integrations.datalog import DataLOGIntegration
from src.integrations.datalogviewer import DataLogViewerIntegration

__all__ = [
    # Base Classes
    'BaseIntegration',
    'LogEntry',
    'PerformanceMetric',

    # Cloud Platforms
    'CloudWatchIntegration',
    'AzureMonitorIntegration',

    # APM & Monitoring
    'DataDogIntegration',
    'DynatraceIntegration',

    # SIEM & Security
    'SplunkIntegration',
    'SolarWindsIntegration',
    'SentryIntegration',
    'HuntressIntegration',

    # Elastic Stack
    'ElasticIntegration',
    'LogstashIntegration',

    # Metrics & Visualization
    'PrometheusIntegration',
    'GrafanaIntegration',

    # Log Aggregation SaaS
    'SumoLogicIntegration',
    'LogglyIntegration',
    'PapertrailIntegration',
    'CoralogixIntegration',
    'LumigoIntegration',

    # Log Collection & Processing
    'FluentdIntegration',

    # Application Performance
    'RetraceIntegration',

    # Web Analytics
    'GoAccessIntegration',

    # Additional Platforms
    'LogentriesIntegration',
    'VelocityAPIntegration',
    'DataLOGIntegration',
    'DataLogViewerIntegration',
]


# Platform availability mapping
AVAILABLE_PLATFORMS = {
    'cloudwatch': CloudWatchIntegration,
    'azure': AzureMonitorIntegration,
    'datadog': DataDogIntegration,
    'dynatrace': DynatraceIntegration,
    'splunk': SplunkIntegration,
    'solarwinds': SolarWindsIntegration,
    'sentry': SentryIntegration,
    'huntress': HuntressIntegration,
    'elasticsearch': ElasticIntegration,
    'elastic': ElasticIntegration,
    'kibana': ElasticIntegration,  # Kibana uses Elasticsearch backend
    'logstash': LogstashIntegration,
    'prometheus': PrometheusIntegration,
    'grafana': GrafanaIntegration,
    'loki': GrafanaIntegration,  # Loki accessed via Grafana integration
    'sumologic': SumoLogicIntegration,
    'loggly': LogglyIntegration,
    'papertrail': PapertrailIntegration,
    'coralogix': CoralogixIntegration,
    'lumigo': LumigoIntegration,
    'fluentd': FluentdIntegration,
    'retrace': RetraceIntegration,
    'stackify': RetraceIntegration,  # Retrace is Stackify's product
    'goaccess': GoAccessIntegration,
    'logentries': LogentriesIntegration,
    'velocityap': VelocityAPIntegration,
    'datalog': DataLOGIntegration,
    'biometrics': DataLOGIntegration,  # Biometrics Ltd DataLOG
    'datalogviewer': DataLogViewerIntegration,
}


def get_integration(platform: str, config: dict) -> BaseIntegration:
    """
    Factory function to get integration instance by platform name.

    Args:
        platform: Platform name (e.g., 'cloudwatch', 'datadog')
        config: Configuration dictionary for the platform

    Returns:
        Integration instance

    Raises:
        ValueError: If platform is not supported
    """
    platform_lower = platform.lower()

    if platform_lower not in AVAILABLE_PLATFORMS:
        available = ', '.join(sorted(AVAILABLE_PLATFORMS.keys()))
        raise ValueError(
            f"Platform '{platform}' not supported. "
            f"Available platforms: {available}"
        )

    integration_class = AVAILABLE_PLATFORMS[platform_lower]
    return integration_class(config)


def list_available_platforms() -> list:
    """
    Get list of all available platform integrations.

    Returns:
        Sorted list of platform names
    """
    return sorted(AVAILABLE_PLATFORMS.keys())
