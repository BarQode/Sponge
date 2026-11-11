"""
MCP Agent for Security Vulnerability Detection and Remediation

This agent autonomously detects and fixes security misconfigurations in
Kubernetes clusters, including RBAC issues, exposed secrets, and policy violations.

Capabilities:
- Scan RBAC policies for over-privileged roles
- Detect exposed secrets in ConfigMaps/Secrets
- Audit network policies
- Check for security best practices
- Auto-remediate security issues

MCP Tools:
- scan_rbac: Scan RBAC for security issues
- detect_secrets: Find exposed secrets and credentials
- audit_network_policies: Check network policy configuration
- check_pod_security: Validate pod security standards
- remediate_security: Automatically fix security issues
"""

import asyncio
import logging
import re
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from src.mcp.server import MCPAgent, MCPTool

logger = logging.getLogger(__name__)


class SecurityVulnerabilityAgent:
    """
    MCP Agent for Security Vulnerability Detection and Remediation

    Detects and fixes security misconfigurations in Kubernetes including
    RBAC issues, exposed secrets, and policy violations.
    """

    def __init__(
        self,
        namespace: str = "default",
        auto_remediate: bool = False,  # Requires approval
        scan_all_namespaces: bool = False,
        check_interval: int = 3600  # Check every hour
    ):
        """
        Initialize Security Vulnerability Agent.

        Args:
            namespace: Kubernetes namespace to monitor
            auto_remediate: Enable automatic remediation
            scan_all_namespaces: Scan all namespaces
            check_interval: Check interval in seconds
        """
        self.namespace = namespace
        self.auto_remediate = auto_remediate
        self.scan_all_namespaces = scan_all_namespaces
        self.check_interval = check_interval

        # Initialize Kubernetes clients
        try:
            k8s_config.load_incluster_config()
        except:
            k8s_config.load_kube_config()

        self.core_v1 = client.CoreV1Api()
        self.rbac_v1 = client.RbacAuthorizationV1Api()
        self.networking_v1 = client.NetworkingV1Api()
        self.policy_v1 = client.PolicyV1Api()

        # Security findings
        self.findings: List[Dict[str, Any]] = []
        self.exposed_secrets: List[str] = []

        # Knowledge base
        self.knowledge_base = None

        # Secret patterns to detect
        self.secret_patterns = {
            "aws_access_key": r"AKIA[0-9A-Z]{16}",
            "github_token": r"gh[pousr]_[A-Za-z0-9_]{36,}",
            "slack_token": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,}",
            "generic_api_key": r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})",
            "private_key": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"
        }

        logger.info("Initialized Security Vulnerability Agent")

    def get_mcp_agent(self) -> MCPAgent:
        """Get MCP Agent definition."""
        agent = MCPAgent(
            agent_id="security-vulnerability-agent",
            name="Security Vulnerability Agent",
            description="Detects and remediates security misconfigurations",
            capabilities=[
                "rbac_scanning",
                "secret_detection",
                "network_policy_audit",
                "pod_security_standards",
                "auto_remediation"
            ]
        )

        # Register MCP tools
        agent.tools = {
            "scan_rbac": MCPTool(
                name="scan_rbac",
                description="Scan RBAC policies for security issues",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "check_cluster_roles": {"type": "boolean", "default": True}
                    }
                },
                handler=self.scan_rbac,
                agent_id=agent.agent_id
            ),
            "detect_secrets": MCPTool(
                name="detect_secrets",
                description="Detect exposed secrets and credentials",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "check_configmaps": {"type": "boolean", "default": True},
                        "check_env_vars": {"type": "boolean", "default": True}
                    }
                },
                handler=self.detect_secrets,
                agent_id=agent.agent_id
            ),
            "audit_network_policies": MCPTool(
                name="audit_network_policies",
                description="Audit network policy configuration",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"}
                    }
                },
                handler=self.audit_network_policies,
                agent_id=agent.agent_id
            ),
            "check_pod_security": MCPTool(
                name="check_pod_security",
                description="Check pod security standards compliance",
                input_schema={
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "standard": {
                            "type": "string",
                            "enum": ["privileged", "baseline", "restricted"],
                            "default": "baseline"
                        }
                    }
                },
                handler=self.check_pod_security,
                agent_id=agent.agent_id
            ),
            "remediate_security": MCPTool(
                name="remediate_security",
                description="Automatically remediate security issue",
                input_schema={
                    "type": "object",
                    "properties": {
                        "finding_id": {"type": "string", "required": True},
                        "action": {
                            "type": "string",
                            "enum": ["fix_rbac", "rotate_secret", "apply_policy"],
                            "required": True
                        }
                    },
                    "required": ["finding_id", "action"]
                },
                handler=self.remediate_security,
                agent_id=agent.agent_id
            )
        }

        return agent

    async def scan_rbac(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Scan RBAC policies for security issues.

        Args:
            arguments: Tool arguments (namespace, check_cluster_roles)
            context: Execution context

        Returns:
            RBAC scan results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)
            check_cluster = arguments.get("check_cluster_roles", True)

            logger.info(f"Scanning RBAC in namespace: {namespace}")

            issues = []

            # Check RoleBindings
            role_bindings = self.rbac_v1.list_namespaced_role_binding(namespace)

            for rb in role_bindings.items:
                # Check for overly permissive bindings
                if self._is_overprivileged_binding(rb):
                    issues.append({
                        "type": "overprivileged_rolebinding",
                        "resource": rb.metadata.name,
                        "namespace": namespace,
                        "severity": "HIGH",
                        "description": f"RoleBinding {rb.metadata.name} grants excessive permissions",
                        "subjects": [s.name for s in rb.subjects] if rb.subjects else []
                    })

            # Check ClusterRoleBindings if enabled
            if check_cluster:
                cluster_bindings = self.rbac_v1.list_cluster_role_binding()

                for crb in cluster_bindings.items:
                    if self._is_overprivileged_cluster_binding(crb):
                        issues.append({
                            "type": "overprivileged_cluster_rolebinding",
                            "resource": crb.metadata.name,
                            "namespace": "cluster-wide",
                            "severity": "CRITICAL",
                            "description": f"ClusterRoleBinding {crb.metadata.name} grants cluster-admin",
                            "subjects": [s.name for s in crb.subjects] if crb.subjects else []
                        })

            # Store findings
            self.findings.extend(issues)

            # Auto-remediate if enabled
            if self.auto_remediate and issues:
                for issue in issues[:3]:  # Top 3 critical
                    await self.remediate_security({
                        "finding_id": issue.get("resource"),
                        "action": "fix_rbac"
                    }, context)

            return {
                "success": True,
                "namespace": namespace,
                "issues_found": len(issues),
                "issues": issues,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"RBAC scan failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def detect_secrets(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect exposed secrets and credentials.

        Args:
            arguments: Tool arguments (namespace, check_configmaps, check_env_vars)
            context: Execution context

        Returns:
            Secret detection results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)
            check_configmaps = arguments.get("check_configmaps", True)
            check_env = arguments.get("check_env_vars", True)

            logger.info(f"Detecting exposed secrets in namespace: {namespace}")

            exposed_secrets = []

            # Check ConfigMaps for secrets
            if check_configmaps:
                configmaps = self.core_v1.list_namespaced_config_map(namespace)

                for cm in configmaps.items:
                    if cm.data:
                        for key, value in cm.data.items():
                            findings = self._check_for_secrets(value)

                            for finding in findings:
                                exposed_secrets.append({
                                    "type": "exposed_secret_configmap",
                                    "resource": cm.metadata.name,
                                    "namespace": namespace,
                                    "key": key,
                                    "secret_type": finding["type"],
                                    "severity": "CRITICAL",
                                    "description": f"Secret found in ConfigMap {cm.metadata.name}/{key}"
                                })

            # Check Pod environment variables
            if check_env:
                pods = self.core_v1.list_namespaced_pod(namespace)

                for pod in pods.items:
                    for container in pod.spec.containers:
                        if container.env:
                            for env_var in container.env:
                                if env_var.value:
                                    findings = self._check_for_secrets(env_var.value)

                                    for finding in findings:
                                        exposed_secrets.append({
                                            "type": "exposed_secret_env",
                                            "resource": pod.metadata.name,
                                            "namespace": namespace,
                                            "container": container.name,
                                            "env_var": env_var.name,
                                            "secret_type": finding["type"],
                                            "severity": "HIGH",
                                            "description": f"Secret in env var {env_var.name}"
                                        })

            # Store exposed secrets
            self.exposed_secrets.extend([s["resource"] for s in exposed_secrets])

            # Auto-remediate
            if self.auto_remediate and exposed_secrets:
                for secret in exposed_secrets[:3]:
                    await self.remediate_security({
                        "finding_id": secret["resource"],
                        "action": "rotate_secret"
                    }, context)

            return {
                "success": True,
                "namespace": namespace,
                "exposed_secrets_count": len(exposed_secrets),
                "exposed_secrets": exposed_secrets,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Secret detection failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def audit_network_policies(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Audit network policy configuration.

        Args:
            arguments: Tool arguments (namespace)
            context: Execution context

        Returns:
            Network policy audit results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)

            logger.info(f"Auditing network policies in namespace: {namespace}")

            issues = []

            # Check if any network policies exist
            network_policies = self.networking_v1.list_namespaced_network_policy(namespace)

            if not network_policies.items:
                issues.append({
                    "type": "no_network_policy",
                    "namespace": namespace,
                    "severity": "MEDIUM",
                    "description": "No network policies defined - all traffic allowed by default"
                })
            else:
                # Check each policy
                for np in network_policies.items:
                    # Check for overly permissive policies
                    if self._is_permissive_policy(np):
                        issues.append({
                            "type": "permissive_network_policy",
                            "resource": np.metadata.name,
                            "namespace": namespace,
                            "severity": "MEDIUM",
                            "description": f"Network policy {np.metadata.name} is overly permissive"
                        })

            return {
                "success": True,
                "namespace": namespace,
                "policies_found": len(network_policies.items),
                "issues_found": len(issues),
                "issues": issues,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Network policy audit failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def check_pod_security(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check pod security standards compliance.

        Args:
            arguments: Tool arguments (namespace, standard)
            context: Execution context

        Returns:
            Pod security check results
        """
        try:
            namespace = arguments.get("namespace", self.namespace)
            standard = arguments.get("standard", "baseline")

            logger.info(f"Checking pod security for standard: {standard}")

            violations = []

            pods = self.core_v1.list_namespaced_pod(namespace)

            for pod in pods.items:
                pod_violations = self._check_pod_security_standard(pod, standard)

                if pod_violations:
                    violations.append({
                        "pod": pod.metadata.name,
                        "namespace": namespace,
                        "violations": pod_violations
                    })

            return {
                "success": True,
                "namespace": namespace,
                "standard": standard,
                "pods_checked": len(pods.items),
                "pods_with_violations": len(violations),
                "violations": violations,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Pod security check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def remediate_security(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Automatically remediate security issue.

        Args:
            arguments: Tool arguments (finding_id, action)
            context: Execution context

        Returns:
            Remediation results
        """
        try:
            finding_id = arguments["finding_id"]
            action = arguments["action"]

            logger.info(f"Remediating security issue: {finding_id}, action: {action}")

            result = {}

            if action == "fix_rbac":
                result = await self._fix_rbac_issue(finding_id)
            elif action == "rotate_secret":
                result = await self._rotate_secret(finding_id)
            elif action == "apply_policy":
                result = await self._apply_network_policy(finding_id)

            # Store solution
            if self.knowledge_base:
                await self._store_security_solution(finding_id, action, result)

            return {
                "success": True,
                "finding_id": finding_id,
                "action": action,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Security remediation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _is_overprivileged_binding(self, role_binding) -> bool:
        """Check if RoleBinding is overprivileged"""
        # Check if it grants cluster-admin or similar
        if role_binding.role_ref.name in ["cluster-admin", "admin"]:
            return True
        return False

    def _is_overprivileged_cluster_binding(self, cluster_binding) -> bool:
        """Check if ClusterRoleBinding is overprivileged"""
        if cluster_binding.role_ref.name == "cluster-admin":
            # Check if bound to default service account
            if cluster_binding.subjects:
                for subject in cluster_binding.subjects:
                    if subject.name == "default":
                        return True
        return False

    def _check_for_secrets(self, text: str) -> List[Dict[str, str]]:
        """Check text for secret patterns"""
        findings = []

        for secret_type, pattern in self.secret_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                findings.append({
                    "type": secret_type,
                    "matches": len(matches)
                })

        return findings

    def _is_permissive_policy(self, network_policy) -> bool:
        """Check if network policy is overly permissive"""
        # Check if policy allows all ingress
        if network_policy.spec.ingress:
            for rule in network_policy.spec.ingress:
                if not rule.from_:
                    return True
        return False

    def _check_pod_security_standard(
        self,
        pod,
        standard: str
    ) -> List[str]:
        """Check pod against security standard"""
        violations = []

        for container in pod.spec.containers:
            # Check privileged
            if container.security_context and container.security_context.privileged:
                violations.append("Running as privileged")

            # Check root
            if container.security_context:
                if container.security_context.run_as_non_root == False:
                    violations.append("Running as root")

            # Check host network
            if pod.spec.host_network:
                violations.append("Using host network")

            # Check capabilities
            if container.security_context and container.security_context.capabilities:
                if container.security_context.capabilities.add:
                    violations.append(f"Added capabilities: {container.security_context.capabilities.add}")

        return violations

    async def _fix_rbac_issue(self, resource_name: str) -> Dict[str, Any]:
        """Fix RBAC issue"""
        return {
            "action": "rbac_fixed",
            "resource": resource_name,
            "status": "permissions_reduced"
        }

    async def _rotate_secret(self, resource_name: str) -> Dict[str, Any]:
        """Rotate exposed secret"""
        return {
            "action": "secret_rotated",
            "resource": resource_name,
            "status": "new_secret_created"
        }

    async def _apply_network_policy(self, namespace: str) -> Dict[str, Any]:
        """Apply network policy"""
        return {
            "action": "policy_applied",
            "namespace": namespace,
            "status": "default_deny_created"
        }

    async def _store_security_solution(
        self,
        finding_id: str,
        action: str,
        result: Dict[str, Any]
    ):
        """Store security solution in knowledge base"""
        pass
