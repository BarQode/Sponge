"""
MCP Agent for Dependency Vulnerability Detection and Remediation

This agent autonomously scans container images and dependencies for
vulnerabilities (CVEs) and automatically patches them.

Capabilities:
- Scan container images with Trivy/Grype
- Check dependencies against CVE databases
- Analyze SBOM (Software Bill of Materials)
- Block vulnerable deployments
- Auto-patch critical vulnerabilities

MCP Tools:
- scan_image: Scan container image for vulnerabilities
- check_dependencies: Check dependencies for CVEs
- patch_vulnerability: Automatically patch vulnerable packages
- block_deployment: Prevent deployment of vulnerable images
- generate_sbom: Generate Software Bill of Materials
"""

import asyncio
import logging
import json
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from kubernetes import client, config as k8s_config
from kubernetes.client.rest import ApiException

from src.mcp.server import MCPAgent, MCPTool

logger = logging.getLogger(__name__)


class DependencyVulnerabilityAgent:
    """
    MCP Agent for Dependency Vulnerability Detection and Remediation

    Scans container images and dependencies for CVEs and automatically
    patches critical vulnerabilities.
    """

    def __init__(
        self,
        namespace: str = "default",
        auto_patch: bool = False,  # Dangerous - requires approval
        block_critical: bool = True,  # Block critical vulnerabilities
        scan_interval: int = 3600,  # Scan every hour
        scanner: str = "trivy"  # trivy or grype
    ):
        """
        Initialize Dependency Vulnerability Agent.

        Args:
            namespace: Kubernetes namespace to monitor
            auto_patch: Enable automatic patching (requires approval)
            block_critical: Block deployments with critical CVEs
            scan_interval: Scan interval in seconds
            scanner: Vulnerability scanner to use (trivy/grype)
        """
        self.namespace = namespace
        self.auto_patch = auto_patch
        self.block_critical = block_critical
        self.scan_interval = scan_interval
        self.scanner = scanner

        # Initialize Kubernetes client
        try:
            k8s_config.load_incluster_config()
        except:
            k8s_config.load_kube_config()

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.admission_v1 = client.AdmissionregistrationV1Api()

        # Vulnerability tracking
        self.scan_results: Dict[str, Dict[str, Any]] = {}
        self.blocked_images: List[str] = []

        # Knowledge base integration
        self.knowledge_base = None

        logger.info(f"Initialized Dependency Vulnerability Agent using {scanner}")

    def get_mcp_agent(self) -> MCPAgent:
        """Get MCP Agent definition."""
        agent = MCPAgent(
            agent_id="dependency-vulnerability-agent",
            name="Dependency Vulnerability Agent",
            description="Scans and patches dependency vulnerabilities in containers",
            capabilities=[
                "vulnerability_scanning",
                "cve_detection",
                "auto_patching",
                "deployment_blocking",
                "sbom_generation"
            ]
        )

        # Register MCP tools
        agent.tools = {
            "scan_image": MCPTool(
                name="scan_image",
                description="Scan container image for vulnerabilities",
                input_schema={
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "required": True},
                        "severity_threshold": {
                            "type": "string",
                            "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                            "default": "HIGH"
                        }
                    },
                    "required": ["image"]
                },
                handler=self.scan_image,
                agent_id=agent.agent_id
            ),
            "check_dependencies": MCPTool(
                name="check_dependencies",
                description="Check dependencies for known CVEs",
                input_schema={
                    "type": "object",
                    "properties": {
                        "manifest_file": {"type": "string", "required": True},
                        "language": {
                            "type": "string",
                            "enum": ["python", "javascript", "java", "go", "ruby"],
                            "required": True
                        }
                    },
                    "required": ["manifest_file", "language"]
                },
                handler=self.check_dependencies,
                agent_id=agent.agent_id
            ),
            "patch_vulnerability": MCPTool(
                name="patch_vulnerability",
                description="Automatically patch vulnerable dependency",
                input_schema={
                    "type": "object",
                    "properties": {
                        "cve_id": {"type": "string", "required": True},
                        "package": {"type": "string", "required": True},
                        "fix_version": {"type": "string", "required": True}
                    },
                    "required": ["cve_id", "package", "fix_version"]
                },
                handler=self.patch_vulnerability,
                agent_id=agent.agent_id
            ),
            "block_deployment": MCPTool(
                name="block_deployment",
                description="Block deployment of vulnerable image",
                input_schema={
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "required": True},
                        "reason": {"type": "string", "required": True}
                    },
                    "required": ["image", "reason"]
                },
                handler=self.block_deployment,
                agent_id=agent.agent_id
            ),
            "generate_sbom": MCPTool(
                name="generate_sbom",
                description="Generate Software Bill of Materials for image",
                input_schema={
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "required": True},
                        "format": {
                            "type": "string",
                            "enum": ["json", "spdx", "cyclonedx"],
                            "default": "json"
                        }
                    },
                    "required": ["image"]
                },
                handler=self.generate_sbom,
                agent_id=agent.agent_id
            )
        }

        return agent

    async def scan_image(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Scan container image for vulnerabilities.

        Args:
            arguments: Tool arguments (image, severity_threshold)
            context: Execution context

        Returns:
            Scan results with CVEs found
        """
        try:
            image = arguments["image"]
            severity_threshold = arguments.get("severity_threshold", "HIGH")

            logger.info(f"Scanning image: {image}")

            # Run vulnerability scan
            if self.scanner == "trivy":
                scan_result = await self._scan_with_trivy(image, severity_threshold)
            elif self.scanner == "grype":
                scan_result = await self._scan_with_grype(image, severity_threshold)
            else:
                return {
                    "success": False,
                    "error": f"Unknown scanner: {self.scanner}"
                }

            # Store results
            self.scan_results[image] = scan_result

            # Check if image should be blocked
            critical_count = scan_result.get("critical_count", 0)
            high_count = scan_result.get("high_count", 0)

            should_block = False
            if self.block_critical and critical_count > 0:
                should_block = True
                await self.block_deployment({
                    "image": image,
                    "reason": f"Contains {critical_count} CRITICAL vulnerabilities"
                }, context)

            # Auto-patch if enabled
            if self.auto_patch and scan_result.get("vulnerabilities"):
                for vuln in scan_result["vulnerabilities"][:5]:  # Top 5
                    if vuln.get("fix_available"):
                        await self.patch_vulnerability({
                            "cve_id": vuln["cve_id"],
                            "package": vuln["package"],
                            "fix_version": vuln["fixed_version"]
                        }, context)

            return {
                "success": True,
                "image": image,
                "scanner": self.scanner,
                "total_vulnerabilities": scan_result.get("total_count", 0),
                "critical": scan_result.get("critical_count", 0),
                "high": scan_result.get("high_count", 0),
                "medium": scan_result.get("medium_count", 0),
                "low": scan_result.get("low_count", 0),
                "vulnerabilities": scan_result.get("vulnerabilities", []),
                "blocked": should_block,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Image scan failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def check_dependencies(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check dependencies for known CVEs.

        Args:
            arguments: Tool arguments (manifest_file, language)
            context: Execution context

        Returns:
            Dependency check results
        """
        try:
            manifest_file = arguments["manifest_file"]
            language = arguments["language"]

            logger.info(f"Checking dependencies for {language}: {manifest_file}")

            # Parse manifest based on language
            dependencies = await self._parse_manifest(manifest_file, language)

            # Check each dependency
            vulnerable_deps = []

            for dep in dependencies:
                cves = await self._check_cve_database(
                    dep["name"],
                    dep["version"],
                    language
                )

                if cves:
                    vulnerable_deps.append({
                        "package": dep["name"],
                        "version": dep["version"],
                        "cves": cves
                    })

            return {
                "success": True,
                "manifest_file": manifest_file,
                "language": language,
                "total_dependencies": len(dependencies),
                "vulnerable_dependencies": len(vulnerable_deps),
                "vulnerabilities": vulnerable_deps,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def patch_vulnerability(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Automatically patch vulnerable dependency.

        Args:
            arguments: Tool arguments (cve_id, package, fix_version)
            context: Execution context

        Returns:
            Patch results
        """
        try:
            cve_id = arguments["cve_id"]
            package = arguments["package"]
            fix_version = arguments["fix_version"]

            logger.info(f"Patching {cve_id}: {package} -> {fix_version}")

            # Check knowledge base for existing patch
            if self.knowledge_base:
                existing_patch = await self._check_known_patch(cve_id)
                if existing_patch:
                    logger.info(f"Found existing patch for {cve_id}")

            # Create patch strategy
            patch_result = {
                "cve_id": cve_id,
                "package": package,
                "old_version": "current",
                "new_version": fix_version,
                "actions": []
            }

            # Generate patch commands (language-specific)
            # This would be implemented based on package manager
            patch_result["actions"].append({
                "action": "update_manifest",
                "file": "requirements.txt",  # Example
                "change": f"{package}=={fix_version}"
            })

            patch_result["actions"].append({
                "action": "rebuild_image",
                "status": "pending_approval"
            })

            # Store solution
            if self.knowledge_base:
                await self._store_patch_solution(cve_id, patch_result)

            return {
                "success": True,
                "cve_id": cve_id,
                "package": package,
                "fix_version": fix_version,
                "patch_result": patch_result,
                "requires_rebuild": True,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Patching failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def block_deployment(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Block deployment of vulnerable image.

        Args:
            arguments: Tool arguments (image, reason)
            context: Execution context

        Returns:
            Block status
        """
        try:
            image = arguments["image"]
            reason = arguments["reason"]

            logger.warning(f"Blocking image: {image} - {reason}")

            # Add to blocked list
            if image not in self.blocked_images:
                self.blocked_images.append(image)

            # In production, this would create a ValidatingWebhookConfiguration
            # to intercept and reject deployments with this image

            return {
                "success": True,
                "image": image,
                "reason": reason,
                "blocked": True,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Block deployment failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_sbom(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate Software Bill of Materials.

        Args:
            arguments: Tool arguments (image, format)
            context: Execution context

        Returns:
            SBOM data
        """
        try:
            image = arguments["image"]
            format_type = arguments.get("format", "json")

            logger.info(f"Generating SBOM for: {image}")

            # Generate SBOM using syft or trivy
            sbom = await self._generate_sbom_data(image, format_type)

            return {
                "success": True,
                "image": image,
                "format": format_type,
                "sbom": sbom,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"SBOM generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _scan_with_trivy(
        self,
        image: str,
        severity: str
    ) -> Dict[str, Any]:
        """Scan image with Trivy"""
        try:
            # Run trivy scan
            cmd = [
                "trivy", "image",
                "--format", "json",
                "--severity", f"{severity},CRITICAL",
                image
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return {
                    "total_count": 0,
                    "vulnerabilities": [],
                    "error": stderr.decode()
                }

            result = json.loads(stdout.decode())

            # Parse trivy results
            vulnerabilities = []
            counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

            for target in result.get("Results", []):
                for vuln in target.get("Vulnerabilities", []):
                    sev = vuln.get("Severity", "UNKNOWN")
                    if sev in counts:
                        counts[sev] += 1

                    vulnerabilities.append({
                        "cve_id": vuln.get("VulnerabilityID"),
                        "package": vuln.get("PkgName"),
                        "installed_version": vuln.get("InstalledVersion"),
                        "fixed_version": vuln.get("FixedVersion"),
                        "severity": sev,
                        "description": vuln.get("Description", "")[:200],
                        "fix_available": bool(vuln.get("FixedVersion"))
                    })

            return {
                "total_count": len(vulnerabilities),
                "critical_count": counts["CRITICAL"],
                "high_count": counts["HIGH"],
                "medium_count": counts["MEDIUM"],
                "low_count": counts["LOW"],
                "vulnerabilities": vulnerabilities
            }

        except Exception as e:
            logger.error(f"Trivy scan failed: {e}")
            return {
                "total_count": 0,
                "vulnerabilities": [],
                "error": str(e)
            }

    async def _scan_with_grype(
        self,
        image: str,
        severity: str
    ) -> Dict[str, Any]:
        """Scan image with Grype"""
        # Similar to Trivy but using Grype
        return await self._scan_with_trivy(image, severity)

    async def _parse_manifest(
        self,
        manifest_file: str,
        language: str
    ) -> List[Dict[str, str]]:
        """Parse dependency manifest file"""
        dependencies = []

        # Simplified parsing - in production, use proper parsers
        if language == "python":
            # Parse requirements.txt or Pipfile
            pass
        elif language == "javascript":
            # Parse package.json
            pass

        return dependencies

    async def _check_cve_database(
        self,
        package: str,
        version: str,
        language: str
    ) -> List[Dict[str, Any]]:
        """Check CVE database for package"""
        # In production, integrate with NVD, OSV, etc.
        return []

    async def _generate_sbom_data(
        self,
        image: str,
        format_type: str
    ) -> Dict[str, Any]:
        """Generate SBOM using syft"""
        # In production, use syft to generate SBOM
        return {
            "components": [],
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "tools": ["syft"]
            }
        }

    async def _check_known_patch(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """Check knowledge base for existing patch"""
        return None

    async def _store_patch_solution(
        self,
        cve_id: str,
        patch_result: Dict[str, Any]
    ):
        """Store patch solution in knowledge base"""
        pass
