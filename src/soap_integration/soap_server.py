"""
SOAP API Server for Sponge RCA Tool

Provides SOAP endpoints for:
- Extracting fixes from knowledge base
- Auto-remediation of detected issues
- Integration with SaaS applications
- Ansible agent coordination
"""

from spyne import Application, rpc, ServiceBase, Integer, Unicode, Array, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


# Complex Types for SOAP
class Fix(ComplexModel):
    """Represents a fix from knowledge base"""
    __namespace__ = "sponge.rca"

    error_pattern = Unicode
    category = Unicode
    severity = Unicode
    solution = Unicode
    implementation_steps = Unicode
    automation_script = Unicode
    confidence = Unicode
    last_updated = Unicode


class RemediationRequest(ComplexModel):
    """Request for auto-remediation"""
    __namespace__ = "sponge.rca"

    issue_id = Unicode
    environment = Unicode  # dev, staging, production
    auto_approve = Unicode  # true/false
    notification_email = Unicode


class RemediationResult(ComplexModel):
    """Result of remediation attempt"""
    __namespace__ = "sponge.rca"

    request_id = Unicode
    status = Unicode  # success, failed, pending
    message = Unicode
    ansible_playbook_path = Unicode
    execution_log = Unicode
    timestamp = Unicode


class Vulnerability(ComplexModel):
    """Detected vulnerability"""
    __namespace__ = "sponge.rca"

    vuln_id = Unicode
    severity = Unicode
    cve_id = Unicode
    description = Unicode
    affected_component = Unicode
    fix_available = Unicode
    remediation_steps = Unicode


class SpongeSOAPService(ServiceBase):
    """Main SOAP service for Sponge RCA Tool"""

    @rpc(Unicode, _returns=Array(Fix))
    def get_fixes_by_category(ctx, category):
        """
        Get all fixes for a specific category

        Args:
            category: Issue category (CPU, Memory, Network, etc.)

        Returns:
            Array of Fix objects
        """
        logger.info(f"SOAP request: get_fixes_by_category({category})")

        try:
            from src.knowledge_base import EnhancedKnowledgeBase

            kb = EnhancedKnowledgeBase()
            results = kb.search({'categories': [category]})

            fixes = []
            for _, row in results.iterrows():
                fix = Fix()
                fix.error_pattern = str(row.get('Error_Pattern', ''))
                fix.category = str(row.get('Category', ''))
                fix.severity = str(row.get('Severity', ''))
                fix.solution = str(row.get('Solution', ''))
                fix.implementation_steps = str(row.get('Implementation_Steps', ''))
                fix.automation_script = ''  # Generated on demand
                fix.confidence = str(row.get('Confidence', ''))
                fix.last_updated = str(row.get('Last_Updated', ''))
                fixes.append(fix)

            logger.info(f"Returning {len(fixes)} fixes")
            return fixes

        except Exception as e:
            logger.error(f"Error getting fixes: {e}")
            return []

    @rpc(Unicode, _returns=Array(Fix))
    def get_critical_fixes(ctx, min_confidence):
        """
        Get all critical fixes above confidence threshold

        Args:
            min_confidence: Minimum confidence score (0.0-1.0)

        Returns:
            Array of critical Fix objects
        """
        logger.info(f"SOAP request: get_critical_fixes({min_confidence})")

        try:
            from src.knowledge_base import EnhancedKnowledgeBase

            kb = EnhancedKnowledgeBase()
            results = kb.search({
                'severities': ['critical'],
                'min_confidence': float(min_confidence),
                'has_solution': True
            })

            fixes = []
            for _, row in results.iterrows():
                fix = Fix()
                fix.error_pattern = str(row.get('Error_Pattern', ''))
                fix.category = str(row.get('Category', ''))
                fix.severity = str(row.get('Severity', ''))
                fix.solution = str(row.get('Solution', ''))
                fix.implementation_steps = str(row.get('Implementation_Steps', ''))
                fix.confidence = str(row.get('Confidence', ''))
                fix.last_updated = str(row.get('Last_Updated', ''))
                fixes.append(fix)

            return fixes

        except Exception as e:
            logger.error(f"Error getting critical fixes: {e}")
            return []

    @rpc(RemediationRequest, _returns=RemediationResult)
    def auto_remediate(ctx, request):
        """
        Automatically remediate a detected issue

        Args:
            request: RemediationRequest with issue details

        Returns:
            RemediationResult with execution status
        """
        logger.info(f"SOAP request: auto_remediate({request.issue_id})")

        result = RemediationResult()
        result.request_id = f"REM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result.timestamp = datetime.now().isoformat()

        try:
            # Import remediation agent
            from src.soap_integration.remediation_agent import RemediationAgent

            agent = RemediationAgent()

            # Execute remediation
            execution_result = agent.execute_remediation(
                issue_id=request.issue_id,
                environment=request.environment,
                auto_approve=(request.auto_approve.lower() == 'true')
            )

            result.status = execution_result['status']
            result.message = execution_result['message']
            result.ansible_playbook_path = execution_result.get('playbook_path', '')
            result.execution_log = execution_result.get('log', '')

            # Send notification if email provided
            if request.notification_email:
                agent.send_notification(request.notification_email, execution_result)

            return result

        except Exception as e:
            logger.error(f"Auto-remediation failed: {e}")
            result.status = 'failed'
            result.message = str(e)
            return result

    @rpc(Unicode, _returns=Array(Vulnerability))
    def scan_vulnerabilities(ctx, target_environment):
        """
        Scan for vulnerabilities in target environment

        Args:
            target_environment: Environment to scan

        Returns:
            Array of detected vulnerabilities
        """
        logger.info(f"SOAP request: scan_vulnerabilities({target_environment})")

        try:
            from src.soap_integration.vulnerability_scanner import VulnerabilityScanner

            scanner = VulnerabilityScanner()
            scan_results = scanner.scan_environment(target_environment)

            vulnerabilities = []
            for vuln_data in scan_results:
                vuln = Vulnerability()
                vuln.vuln_id = vuln_data['id']
                vuln.severity = vuln_data['severity']
                vuln.cve_id = vuln_data.get('cve_id', '')
                vuln.description = vuln_data['description']
                vuln.affected_component = vuln_data['component']
                vuln.fix_available = str(vuln_data['fix_available'])
                vuln.remediation_steps = json.dumps(vuln_data.get('remediation', []))
                vulnerabilities.append(vuln)

            return vulnerabilities

        except Exception as e:
            logger.error(f"Vulnerability scan failed: {e}")
            return []

    @rpc(Unicode, Unicode, _returns=Unicode)
    def update_certificates(ctx, domain, cert_type):
        """
        Auto-renew certificates for domain

        Args:
            domain: Domain name
            cert_type: Certificate type (ssl, tls, etc.)

        Returns:
            Status message
        """
        logger.info(f"SOAP request: update_certificates({domain}, {cert_type})")

        try:
            from src.soap_integration.certificate_manager import CertificateManager

            manager = CertificateManager()
            result = manager.renew_certificate(domain, cert_type)

            return f"Certificate renewed: {result['status']}"

        except Exception as e:
            logger.error(f"Certificate renewal failed: {e}")
            return f"Failed: {str(e)}"

    @rpc(Unicode, _returns=Unicode)
    def restart_containers(ctx, container_pattern):
        """
        Restart containers matching pattern

        Args:
            container_pattern: Pattern to match container names

        Returns:
            Status message
        """
        logger.info(f"SOAP request: restart_containers({container_pattern})")

        try:
            from src.soap_integration.container_manager import ContainerLifecycleManager

            manager = ContainerLifecycleManager()
            result = manager.restart_containers(container_pattern)

            return f"Restarted {result['count']} containers"

        except Exception as e:
            logger.error(f"Container restart failed: {e}")
            return f"Failed: {str(e)}"

    @rpc(_returns=Unicode)
    def health_check(ctx):
        """Health check endpoint"""
        return "healthy"


def create_soap_app():
    """Create SOAP application"""
    application = Application(
        [SpongeSOAPService],
        tns='sponge.rca',
        in_protocol=Soap11(validator='lxml'),
        out_protocol=Soap11()
    )

    return application


def run_soap_server(host='0.0.0.0', port=8001):
    """Run SOAP server"""
    from wsgiref.simple_server import make_server

    application = create_soap_app()
    wsgi_app = WsgiApplication(application)

    server = make_server(host, port, wsgi_app)

    logger.info(f"SOAP server running on http://{host}:{port}")
    logger.info(f"WSDL available at http://{host}:{port}/?wsdl")

    server.serve_forever()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_soap_server()
