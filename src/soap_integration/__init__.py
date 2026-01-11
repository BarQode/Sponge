"""
SOAP Integration Module

Provides SOAP API and auto-remediation agents for SaaS integration.
"""

from .soap_server import SpongeSOAPService, create_soap_app, run_soap_server
from .remediation_agent import RemediationAgent
from .vulnerability_scanner import VulnerabilityScanner
from .certificate_manager import CertificateManager
from .container_manager import ContainerLifecycleManager

__all__ = [
    'SpongeSOAPService',
    'create_soap_app',
    'run_soap_server',
    'RemediationAgent',
    'VulnerabilityScanner',
    'CertificateManager',
    'ContainerLifecycleManager'
]
