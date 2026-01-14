"""
Security Automation Module for Cybersecurity Toil Reduction

This module implements automated security operations:
- Just-in-Time (JIT) access control with ChatOps
- Security Orchestration, Automation, and Response (SOAR)
- Compliance as Code with continuous auditing
- Threat intelligence integration
- Automated incident response
"""

from .jit_access import JITAccessManager, AccessRequest, AccessGrant
from .soar_engine import SOAREngine, SOARPlaybook, SecurityIncident
from .compliance_scanner import ComplianceScanner, CompliancePolicy, ComplianceViolation
from .threat_intelligence import ThreatIntelligence, ThreatIndicator, IPReputation

__all__ = [
    'JITAccessManager',
    'AccessRequest',
    'AccessGrant',
    'SOAREngine',
    'SOARPlaybook',
    'SecurityIncident',
    'ComplianceScanner',
    'CompliancePolicy',
    'ComplianceViolation',
    'ThreatIntelligence',
    'ThreatIndicator',
    'IPReputation'
]

__version__ = '1.0.0'
