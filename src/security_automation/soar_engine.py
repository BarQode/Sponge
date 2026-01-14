"""
SOAR Engine - Security Orchestration, Automation, and Response

Automates security incident response workflows with playbooks
for common threats (suspicious IPs, malware, phishing, etc.)
"""

import logging
import json
import sqlite3
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SecurityIncident:
    """Security incident detected by monitoring systems"""
    incident_id: str
    incident_type: str  # 'suspicious_ip', 'malware', 'phishing', 'brute_force', etc.
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    indicators: Dict[str, Any]  # IOCs (IP, domain, hash, etc.)
    detected_at: datetime
    status: str  # 'new', 'investigating', 'contained', 'resolved'
    automated_actions: List[str]


@dataclass
class SOARPlaybook:
    """Automated playbook for incident response"""
    name: str
    incident_type: str
    steps: List[Dict[str, Any]]
    auto_execute: bool  # Whether to execute without approval
    escalation_threshold: str  # Severity level that requires escalation


class SOAREngine:
    """
    Security Orchestration, Automation, and Response Engine

    Automatically responds to security incidents using playbooks.
    Integrates with threat intelligence and enforcement systems (WAF, firewall).
    """

    def __init__(self, db_path: str = "data/soar_incidents.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self.playbooks: Dict[str, SOARPlaybook] = {}
        self._init_playbooks()

    def _init_database(self):
        """Initialize incident tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT UNIQUE NOT NULL,
                    incident_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    indicators TEXT NOT NULL,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    automated_actions TEXT NOT NULL,
                    resolved_at TIMESTAMP NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS incident_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_details TEXT NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN NOT NULL,
                    result TEXT
                )
            """)

            conn.commit()

    def _init_playbooks(self):
        """Initialize SOAR playbooks for common incidents"""
        self.playbooks = {
            'suspicious_ip': SOARPlaybook(
                name="Suspicious IP Response",
                incident_type="suspicious_ip",
                steps=[
                    {"action": "check_threat_intelligence", "params": {"indicator_type": "ip"}},
                    {"action": "check_reputation", "params": {"service": "virustotal"}},
                    {"action": "block_ip_at_waf", "params": {"duration": "24h"}},
                    {"action": "alert_security_team", "params": {"priority": "high"}},
                    {"action": "check_affected_users", "params": {}},
                    {"action": "force_password_reset", "params": {"if_compromised": True}}
                ],
                auto_execute=True,
                escalation_threshold="critical"
            ),

            'brute_force_attempt': SOARPlaybook(
                name="Brute Force Defense",
                incident_type="brute_force_attempt",
                steps=[
                    {"action": "identify_source_ip", "params": {}},
                    {"action": "block_ip_temporarily", "params": {"duration": "1h"}},
                    {"action": "enable_rate_limiting", "params": {"endpoint": "auth"}},
                    {"action": "notify_affected_user", "params": {}},
                    {"action": "enable_mfa_requirement", "params": {"user": "affected"}}
                ],
                auto_execute=True,
                escalation_threshold="high"
            ),

            'malware_detected': SOARPlaybook(
                name="Malware Containment",
                incident_type="malware_detected",
                steps=[
                    {"action": "isolate_affected_host", "params": {"network_quarantine": True}},
                    {"action": "collect_forensic_data", "params": {"memory_dump": True}},
                    {"action": "scan_file_hash", "params": {"service": "virustotal"}},
                    {"action": "check_propagation", "params": {"scan_network": True}},
                    {"action": "alert_ir_team", "params": {"priority": "critical"}},
                    {"action": "create_incident_ticket", "params": {"type": "security_incident"}}
                ],
                auto_execute=False,  # Requires approval for isolation
                escalation_threshold="medium"
            ),

            'data_exfiltration': SOARPlaybook(
                name="Data Exfiltration Response",
                incident_type="data_exfiltration",
                steps=[
                    {"action": "block_outbound_connection", "params": {}},
                    {"action": "revoke_user_access", "params": {"immediate": True}},
                    {"action": "collect_network_logs", "params": {"last_hours": 24}},
                    {"action": "identify_data_accessed", "params": {}},
                    {"action": "notify_legal_team", "params": {}},
                    {"action": "escalate_to_management", "params": {"priority": "critical"}}
                ],
                auto_execute=True,
                escalation_threshold="low"  # Always escalate
            ),

            'certificate_expiring': SOARPlaybook(
                name="Certificate Renewal",
                incident_type="certificate_expiring",
                steps=[
                    {"action": "check_certificate_status", "params": {}},
                    {"action": "renew_certificate", "params": {"provider": "letsencrypt"}},
                    {"action": "deploy_new_certificate", "params": {}},
                    {"action": "verify_deployment", "params": {}},
                    {"action": "update_monitoring", "params": {}}
                ],
                auto_execute=True,
                escalation_threshold="high"
            )
        }

    def create_incident(self,
                       incident_type: str,
                       severity: str,
                       description: str,
                       indicators: Dict[str, Any]) -> SecurityIncident:
        """
        Create a new security incident

        Args:
            incident_type: Type of incident
            severity: Severity level
            description: Incident description
            indicators: Indicators of compromise (IOCs)

        Returns:
            SecurityIncident object
        """
        incident_id = self._generate_incident_id(incident_type)
        detected_at = datetime.now()

        incident = SecurityIncident(
            incident_id=incident_id,
            incident_type=incident_type,
            severity=severity,
            description=description,
            indicators=indicators,
            detected_at=detected_at,
            status='new',
            automated_actions=[]
        )

        # Store incident
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO security_incidents
                    (incident_id, incident_type, severity, description, indicators,
                     status, automated_actions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (incident.incident_id, incident.incident_type, incident.severity,
                      incident.description, json.dumps(incident.indicators),
                      incident.status, json.dumps(incident.automated_actions)))
                conn.commit()

            logger.info(f"Security incident created: {incident_id} - {incident_type}")

        except Exception as e:
            logger.error(f"Failed to create incident: {e}")

        return incident

    def respond_to_incident(self, incident: SecurityIncident) -> bool:
        """
        Automatically respond to a security incident

        Args:
            incident: Security incident

        Returns:
            True if response successful
        """
        playbook = self.playbooks.get(incident.incident_type)
        if not playbook:
            logger.warning(f"No playbook found for incident type: {incident.incident_type}")
            return False

        logger.info(f"Executing SOAR playbook: {playbook.name} for incident {incident.incident_id}")

        # Check if auto-execution is allowed
        if not playbook.auto_execute:
            logger.info(f"Playbook requires manual approval: {playbook.name}")
            self._escalate_incident(incident, "Manual approval required")
            return False

        # Check if severity requires escalation
        severity_levels = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        if severity_levels.get(incident.severity, 0) >= severity_levels.get(playbook.escalation_threshold, 3):
            logger.warning(f"Incident severity requires escalation: {incident.severity}")
            self._escalate_incident(incident, f"Severity: {incident.severity}")

        # Execute playbook steps
        success_count = 0
        for step in playbook.steps:
            action_result = self._execute_action(
                incident=incident,
                action=step['action'],
                params=step['params']
            )

            if action_result['success']:
                success_count += 1
                incident.automated_actions.append(step['action'])
            else:
                logger.error(f"Action failed: {step['action']} - {action_result.get('error')}")

            # Store action result
            self._record_action(incident.incident_id, step['action'], action_result)

        # Update incident status
        if success_count == len(playbook.steps):
            self._update_incident_status(incident.incident_id, 'resolved')
            logger.info(f"Incident {incident.incident_id} resolved automatically")
            return True
        else:
            self._update_incident_status(incident.incident_id, 'investigating')
            logger.warning(f"Incident {incident.incident_id} partially resolved, requires human intervention")
            return False

    def _execute_action(self,
                       incident: SecurityIncident,
                       action: str,
                       params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single SOAR action"""
        logger.info(f"Executing action: {action}")

        try:
            if action == "check_threat_intelligence":
                return self._check_threat_intelligence(incident.indicators, params)

            elif action == "check_reputation":
                return self._check_reputation(incident.indicators, params)

            elif action == "block_ip_at_waf":
                return self._block_ip_at_waf(incident.indicators.get('ip'), params)

            elif action == "block_ip_temporarily":
                return self._block_ip_temporarily(incident.indicators.get('ip'), params)

            elif action == "alert_security_team":
                return self._alert_security_team(incident, params)

            elif action == "check_affected_users":
                return self._check_affected_users(incident.indicators)

            elif action == "force_password_reset":
                return self._force_password_reset(incident.indicators, params)

            elif action == "isolate_affected_host":
                return self._isolate_host(incident.indicators.get('hostname'), params)

            elif action == "collect_forensic_data":
                return self._collect_forensic_data(incident.indicators, params)

            elif action == "scan_file_hash":
                return self._scan_file_hash(incident.indicators.get('file_hash'), params)

            elif action == "revoke_user_access":
                return self._revoke_user_access(incident.indicators.get('user'), params)

            elif action == "renew_certificate":
                return self._renew_certificate(incident.indicators.get('domain'), params)

            else:
                logger.warning(f"Unknown action: {action}")
                return {'success': False, 'error': f'Unknown action: {action}'}

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {'success': False, 'error': str(e)}

    def _check_threat_intelligence(self, indicators: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Check indicators against threat intelligence feeds"""
        indicator_type = params.get('indicator_type', 'ip')
        indicator_value = indicators.get(indicator_type)

        if not indicator_value:
            return {'success': False, 'error': f'No {indicator_type} indicator found'}

        # Placeholder for actual threat intel integration (AbuseIPDB, AlienVault, etc.)
        logger.info(f"Checking threat intelligence for {indicator_type}: {indicator_value}")

        return {
            'success': True,
            'threat_score': 75,  # Simulated
            'sources': ['simulated_feed'],
            'details': f'Checked {indicator_value} in threat intelligence'
        }

    def _check_reputation(self, indicators: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Check IP/domain reputation"""
        service = params.get('service', 'virustotal')
        ip = indicators.get('ip')

        if not ip:
            return {'success': False, 'error': 'No IP indicator found'}

        logger.info(f"Checking reputation for IP: {ip} using {service}")

        # Placeholder for actual VirusTotal/other API integration
        return {
            'success': True,
            'reputation_score': 'malicious',  # Simulated
            'detections': 15,  # Simulated
            'service': service
        }

    def _block_ip_at_waf(self, ip: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Block IP at WAF level"""
        if not ip:
            return {'success': False, 'error': 'No IP provided'}

        duration = params.get('duration', '24h')

        logger.info(f"Blocking IP at WAF: {ip} for {duration}")

        # Placeholder for actual WAF integration (AWS WAF, Cloudflare, etc.)
        # Example: boto3 WAF integration, Cloudflare API, etc.

        return {
            'success': True,
            'ip': ip,
            'duration': duration,
            'rule_id': f'block_{hashlib.md5(ip.encode()).hexdigest()[:8]}'
        }

    def _block_ip_temporarily(self, ip: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Temporarily block IP (e.g., iptables, firewall)"""
        if not ip:
            return {'success': False, 'error': 'No IP provided'}

        duration = params.get('duration', '1h')

        logger.info(f"Temporarily blocking IP: {ip} for {duration}")

        # Placeholder for actual firewall integration
        return {'success': True, 'ip': ip, 'duration': duration}

    def _alert_security_team(self, incident: SecurityIncident, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send alert to security team"""
        priority = params.get('priority', 'medium')

        logger.info(f"Alerting security team about incident: {incident.incident_id}")

        # Placeholder for actual alerting (PagerDuty, Slack, Email, etc.)
        return {
            'success': True,
            'priority': priority,
            'notified': ['security-team@example.com']
        }

    def _check_affected_users(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Check which users were affected"""
        ip = indicators.get('ip')

        logger.info(f"Checking affected users for IP: {ip}")

        # Placeholder for checking auth logs, etc.
        return {
            'success': True,
            'affected_users': [],  # Simulated
            'login_attempts': 5
        }

    def _force_password_reset(self, indicators: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Force password reset for affected users"""
        if not params.get('if_compromised', False):
            return {'success': True, 'action': 'skipped'}

        logger.info("Forcing password reset for affected users")

        # Placeholder for IAM integration
        return {'success': True, 'users_reset': []}

    def _isolate_host(self, hostname: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Isolate a host from network"""
        if not hostname:
            return {'success': False, 'error': 'No hostname provided'}

        logger.info(f"Isolating host: {hostname}")

        # Placeholder for network isolation (SDN, firewall rules, etc.)
        return {'success': True, 'hostname': hostname, 'isolated': True}

    def _collect_forensic_data(self, indicators: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Collect forensic data from affected host"""
        hostname = indicators.get('hostname')

        logger.info(f"Collecting forensic data from: {hostname}")

        # Placeholder for forensic collection
        return {
            'success': True,
            'data_collected': ['logs', 'memory_dump'] if params.get('memory_dump') else ['logs']
        }

    def _scan_file_hash(self, file_hash: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Scan file hash for malware"""
        if not file_hash:
            return {'success': False, 'error': 'No file hash provided'}

        service = params.get('service', 'virustotal')

        logger.info(f"Scanning file hash: {file_hash} using {service}")

        # Placeholder for VirusTotal API
        return {
            'success': True,
            'malicious': True,  # Simulated
            'detections': 45
        }

    def _revoke_user_access(self, user: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Revoke user access immediately"""
        if not user:
            return {'success': False, 'error': 'No user provided'}

        logger.info(f"Revoking access for user: {user}")

        # Placeholder for IAM integration
        return {'success': True, 'user': user, 'access_revoked': True}

    def _renew_certificate(self, domain: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        """Renew SSL/TLS certificate"""
        if not domain:
            return {'success': False, 'error': 'No domain provided'}

        provider = params.get('provider', 'letsencrypt')

        logger.info(f"Renewing certificate for: {domain} using {provider}")

        # Placeholder for certificate renewal (certbot, ACME, etc.)
        return {'success': True, 'domain': domain, 'provider': provider}

    def _escalate_incident(self, incident: SecurityIncident, reason: str):
        """Escalate incident to security team"""
        logger.warning(f"Escalating incident {incident.incident_id}: {reason}")

        # Update status
        self._update_incident_status(incident.incident_id, 'investigating')

        # Send escalation notification
        # Placeholder for actual escalation (PagerDuty, etc.)

    def _record_action(self, incident_id: str, action: str, result: Dict[str, Any]):
        """Record action result in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO incident_actions
                    (incident_id, action_type, action_details, success, result)
                    VALUES (?, ?, ?, ?, ?)
                """, (incident_id, action, json.dumps(result), result.get('success', False),
                      json.dumps(result)))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to record action: {e}")

    def _update_incident_status(self, incident_id: str, status: str):
        """Update incident status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if status == 'resolved':
                    conn.execute("""
                        UPDATE security_incidents
                        SET status = ?, resolved_at = CURRENT_TIMESTAMP
                        WHERE incident_id = ?
                    """, (status, incident_id))
                else:
                    conn.execute("""
                        UPDATE security_incidents
                        SET status = ?
                        WHERE incident_id = ?
                    """, (status, incident_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update incident status: {e}")

    def _generate_incident_id(self, incident_type: str) -> str:
        """Generate unique incident ID"""
        timestamp = datetime.now().isoformat()
        data = f"{incident_type}:{timestamp}"
        return f"INC-{hashlib.md5(data.encode()).hexdigest()[:12].upper()}"

    def get_active_incidents(self) -> List[SecurityIncident]:
        """Get all active (unresolved) incidents"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT incident_id, incident_type, severity, description,
                           indicators, detected_at, status, automated_actions
                    FROM security_incidents
                    WHERE status != 'resolved'
                    ORDER BY detected_at DESC
                """)

                incidents = []
                for row in cursor.fetchall():
                    incident = SecurityIncident(
                        incident_id=row[0],
                        incident_type=row[1],
                        severity=row[2],
                        description=row[3],
                        indicators=json.loads(row[4]),
                        detected_at=datetime.fromisoformat(row[5]),
                        status=row[6],
                        automated_actions=json.loads(row[7])
                    )
                    incidents.append(incident)

                return incidents

        except Exception as e:
            logger.error(f"Failed to get active incidents: {e}")
            return []
