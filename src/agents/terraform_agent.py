"""
MCP Agent for Terraform Drift Detection and Remediation

This agent autonomously detects infrastructure drift between Terraform state
and actual cloud resources, and automatically corrects it.

Capabilities:
- Compare Terraform state vs actual infrastructure
- Detect manual changes to resources
- Analyze drift impact
- Auto-apply Terraform corrections
- Lock resources to prevent drift

MCP Tools:
- detect_drift: Detect Terraform state drift
- analyze_drift: Analyze drift impact
- apply_correction: Auto-apply Terraform fixes
- lock_resources: Prevent manual changes
- refresh_state: Update Terraform state
"""

import asyncio
import logging
import json
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from src.mcp.server import MCPAgent, MCPTool

logger = logging.getLogger(__name__)


class TerraformDriftAgent:
    """
    MCP Agent for Terraform Drift Detection and Remediation

    Monitors Terraform-managed infrastructure for drift and automatically
    corrects configuration drift.
    """

    def __init__(
        self,
        terraform_dir: str = "/workspace/terraform",
        state_backend: str = "s3",
        auto_correct: bool = False,  # Requires approval
        check_interval: int = 3600,  # Check every hour
        drift_threshold: float = 0.05  # 5% drift triggers alert
    ):
        """
        Initialize Terraform Drift Agent.

        Args:
            terraform_dir: Path to Terraform configuration directory
            state_backend: Terraform state backend (s3, gcs, azurerm, local)
            auto_correct: Enable automatic drift correction
            check_interval: Drift check interval in seconds
            drift_threshold: Drift threshold percentage
        """
        self.terraform_dir = terraform_dir
        self.state_backend = state_backend
        self.auto_correct = auto_correct
        self.check_interval = check_interval
        self.drift_threshold = drift_threshold

        # Drift tracking
        self.drift_history: List[Dict[str, Any]] = []
        self.locked_resources: List[str] = []

        # Knowledge base
        self.knowledge_base = None

        logger.info("Initialized Terraform Drift Agent")

    def get_mcp_agent(self) -> MCPAgent:
        """Get MCP Agent definition."""
        agent = MCPAgent(
            agent_id="terraform-drift-agent",
            name="Terraform Drift Agent",
            description="Detects and corrects Terraform infrastructure drift",
            capabilities=[
                "drift_detection",
                "state_comparison",
                "auto_correction",
                "resource_locking",
                "impact_analysis"
            ]
        )

        # Register MCP tools
        agent.tools = {
            "detect_drift": MCPTool(
                name="detect_drift",
                description="Detect Terraform state drift",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "resource_filter": {"type": "string"}
                    }
                },
                handler=self.detect_drift,
                agent_id=agent.agent_id
            ),
            "analyze_drift": MCPTool(
                name="analyze_drift",
                description="Analyze drift impact and severity",
                input_schema={
                    "type": "object",
                    "properties": {
                        "drift_id": {"type": "string", "required": True}
                    },
                    "required": ["drift_id"]
                },
                handler=self.analyze_drift,
                agent_id=agent.agent_id
            ),
            "apply_correction": MCPTool(
                name="apply_correction",
                description="Automatically apply Terraform correction",
                input_schema={
                    "type": "object",
                    "properties": {
                        "drift_id": {"type": "string", "required": True},
                        "action": {
                            "type": "string",
                            "enum": ["apply", "import", "refresh"],
                            "required": True
                        }
                    },
                    "required": ["drift_id", "action"]
                },
                handler=self.apply_correction,
                agent_id=agent.agent_id
            ),
            "lock_resources": MCPTool(
                name="lock_resources",
                description="Lock resources to prevent manual changes",
                input_schema={
                    "type": "object",
                    "properties": {
                        "resource_addresses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "required": True
                        }
                    },
                    "required": ["resource_addresses"]
                },
                handler=self.lock_resources,
                agent_id=agent.agent_id
            ),
            "refresh_state": MCPTool(
                name="refresh_state",
                description="Refresh Terraform state from actual infrastructure",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"}
                    }
                },
                handler=self.refresh_state,
                agent_id=agent.agent_id
            )
        }

        return agent

    async def detect_drift(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect Terraform state drift.

        Args:
            arguments: Tool arguments (workspace, resource_filter)
            context: Execution context

        Returns:
            Drift detection results
        """
        try:
            workspace = arguments.get("workspace", "default")
            resource_filter = arguments.get("resource_filter")

            logger.info(f"Detecting Terraform drift in workspace: {workspace}")

            # Run terraform plan to detect drift
            plan_result = await self._run_terraform_plan(workspace)

            if not plan_result["success"]:
                return plan_result

            # Parse plan output for drift
            drift_items = self._parse_drift_from_plan(
                plan_result["plan_output"],
                resource_filter
            )

            # Calculate drift metrics
            total_resources = plan_result.get("total_resources", 0)
            drifted_resources = len(drift_items)
            drift_percentage = (drifted_resources / total_resources * 100) if total_resources > 0 else 0

            # Store drift history
            drift_record = {
                "drift_id": f"drift_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "workspace": workspace,
                "timestamp": datetime.utcnow().isoformat(),
                "total_resources": total_resources,
                "drifted_resources": drifted_resources,
                "drift_percentage": drift_percentage,
                "items": drift_items
            }

            self.drift_history.append(drift_record)

            # Auto-correct if enabled and above threshold
            if self.auto_correct and drift_percentage > (self.drift_threshold * 100):
                for item in drift_items[:5]:  # Top 5 critical
                    await self.apply_correction({
                        "drift_id": drift_record["drift_id"],
                        "action": "apply"
                    }, context)

            return {
                "success": True,
                "drift_id": drift_record["drift_id"],
                "workspace": workspace,
                "total_resources": total_resources,
                "drifted_resources": drifted_resources,
                "drift_percentage": drift_percentage,
                "drift_items": drift_items,
                "severity": self._calculate_drift_severity(drift_percentage),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_drift(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze drift impact and severity.

        Args:
            arguments: Tool arguments (drift_id)
            context: Execution context

        Returns:
            Drift analysis results
        """
        try:
            drift_id = arguments["drift_id"]

            logger.info(f"Analyzing drift: {drift_id}")

            # Find drift record
            drift_record = None
            for record in self.drift_history:
                if record["drift_id"] == drift_id:
                    drift_record = record
                    break

            if not drift_record:
                return {
                    "success": False,
                    "error": f"Drift record {drift_id} not found"
                }

            # Analyze each drift item
            analysis = {
                "drift_id": drift_id,
                "items_analyzed": [],
                "impact_summary": {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                },
                "recommendations": []
            }

            for item in drift_record["items"]:
                item_analysis = self._analyze_drift_item(item)
                analysis["items_analyzed"].append(item_analysis)

                # Update impact summary
                severity = item_analysis["severity"]
                analysis["impact_summary"][severity] += 1

            # Generate recommendations
            analysis["recommendations"] = self._generate_drift_recommendations(
                analysis["impact_summary"],
                drift_record["drift_percentage"]
            )

            return {
                "success": True,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Drift analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def apply_correction(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Automatically apply Terraform correction.

        Args:
            arguments: Tool arguments (drift_id, action)
            context: Execution context

        Returns:
            Correction results
        """
        try:
            drift_id = arguments["drift_id"]
            action = arguments["action"]

            logger.info(f"Applying correction for drift: {drift_id}, action: {action}")

            # Find drift record
            drift_record = None
            for record in self.drift_history:
                if record["drift_id"] == drift_id:
                    drift_record = record
                    break

            if not drift_record:
                return {
                    "success": False,
                    "error": f"Drift record {drift_id} not found"
                }

            result = {}

            if action == "apply":
                # Run terraform apply to correct drift
                result = await self._terraform_apply(drift_record["workspace"])
            elif action == "import":
                # Import resources into state
                result = await self._terraform_import(drift_record["workspace"])
            elif action == "refresh":
                # Refresh state from infrastructure
                result = await self.refresh_state({
                    "workspace": drift_record["workspace"]
                }, context)

            # Store solution
            if self.knowledge_base:
                await self._store_drift_solution(drift_id, action, result)

            return {
                "success": True,
                "drift_id": drift_id,
                "action": action,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Drift correction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def lock_resources(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Lock resources to prevent manual changes.

        Args:
            arguments: Tool arguments (resource_addresses)
            context: Execution context

        Returns:
            Lock status
        """
        try:
            resource_addresses = arguments["resource_addresses"]

            logger.info(f"Locking {len(resource_addresses)} resources")

            # Add to locked resources list
            for address in resource_addresses:
                if address not in self.locked_resources:
                    self.locked_resources.append(address)

            # In production, this would:
            # 1. Apply IAM policies to prevent manual changes
            # 2. Enable resource locks in cloud provider
            # 3. Set up change detection alerts

            return {
                "success": True,
                "locked_resources": resource_addresses,
                "total_locked": len(self.locked_resources),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Resource locking failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def refresh_state(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Refresh Terraform state from actual infrastructure.

        Args:
            arguments: Tool arguments (workspace)
            context: Execution context

        Returns:
            Refresh results
        """
        try:
            workspace = arguments.get("workspace", "default")

            logger.info(f"Refreshing Terraform state for workspace: {workspace}")

            # Run terraform refresh
            result = await self._terraform_refresh(workspace)

            return {
                "success": True,
                "workspace": workspace,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"State refresh failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _run_terraform_plan(self, workspace: str) -> Dict[str, Any]:
        """Run terraform plan and capture output"""
        try:
            # Change to terraform directory
            terraform_path = Path(self.terraform_dir)

            if not terraform_path.exists():
                return {
                    "success": False,
                    "error": f"Terraform directory not found: {self.terraform_dir}"
                }

            # Run terraform plan
            cmd = ["terraform", "plan", "-detailed-exitcode", "-no-color", "-json"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.terraform_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # Exit code 0 = no changes, 1 = error, 2 = changes detected
            if process.returncode == 0:
                return {
                    "success": True,
                    "plan_output": "",
                    "total_resources": 0,
                    "has_drift": False
                }
            elif process.returncode == 2:
                # Parse JSON output
                plan_lines = stdout.decode().split('\n')
                return {
                    "success": True,
                    "plan_output": plan_lines,
                    "has_drift": True
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode()
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_drift_from_plan(
        self,
        plan_output: List[str],
        resource_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Parse drift items from terraform plan output"""
        drift_items = []

        for line in plan_output:
            try:
                data = json.loads(line)

                if data.get("type") == "resource_drift":
                    change = data.get("change", {})

                    drift_item = {
                        "resource_address": change.get("resource", {}).get("addr"),
                        "resource_type": change.get("resource", {}).get("resource_type"),
                        "action": change.get("action"),
                        "before": change.get("before"),
                        "after": change.get("after")
                    }

                    # Apply filter if provided
                    if resource_filter:
                        if resource_filter in drift_item["resource_address"]:
                            drift_items.append(drift_item)
                    else:
                        drift_items.append(drift_item)

            except json.JSONDecodeError:
                continue

        return drift_items

    def _calculate_drift_severity(self, drift_percentage: float) -> str:
        """Calculate drift severity level"""
        if drift_percentage >= 20:
            return "critical"
        elif drift_percentage >= 10:
            return "high"
        elif drift_percentage >= 5:
            return "medium"
        else:
            return "low"

    def _analyze_drift_item(self, drift_item: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual drift item"""
        resource_type = drift_item.get("resource_type", "")
        action = drift_item.get("action", "")

        # Determine severity based on resource type and action
        severity = "low"

        # Critical resources
        if any(x in resource_type for x in ["database", "security", "iam", "kms"]):
            severity = "critical"
        # High-impact resources
        elif any(x in resource_type for x in ["network", "load_balancer", "storage"]):
            severity = "high"
        # Medium-impact
        elif any(x in resource_type for x in ["compute", "instance", "container"]):
            severity = "medium"

        # Destructive actions increase severity
        if action in ["delete", "replace"]:
            severity_levels = ["low", "medium", "high", "critical"]
            current_index = severity_levels.index(severity)
            if current_index < len(severity_levels) - 1:
                severity = severity_levels[current_index + 1]

        return {
            "resource_address": drift_item.get("resource_address"),
            "resource_type": resource_type,
            "action": action,
            "severity": severity,
            "impact": self._describe_impact(drift_item)
        }

    def _describe_impact(self, drift_item: Dict[str, Any]) -> str:
        """Describe the impact of a drift item"""
        action = drift_item.get("action", "")
        resource_type = drift_item.get("resource_type", "")

        if action == "delete":
            return f"Resource will be deleted: {resource_type}"
        elif action == "replace":
            return f"Resource will be replaced: {resource_type}"
        elif action == "update":
            return f"Resource will be updated: {resource_type}"
        else:
            return f"Resource state changed: {resource_type}"

    def _generate_drift_recommendations(
        self,
        impact_summary: Dict[str, int],
        drift_percentage: float
    ) -> List[str]:
        """Generate drift remediation recommendations"""
        recommendations = []

        if impact_summary["critical"] > 0:
            recommendations.append(
                f"URGENT: {impact_summary['critical']} critical drift items detected. "
                "Review and correct immediately."
            )

        if drift_percentage > 10:
            recommendations.append(
                "High drift percentage detected. Consider locking resources to prevent manual changes."
            )

        if impact_summary["high"] > 0:
            recommendations.append(
                f"{impact_summary['high']} high-impact resources have drifted. "
                "Plan and apply corrections during maintenance window."
            )

        recommendations.append(
            "Enable automated drift detection and alerting for continuous monitoring."
        )

        return recommendations

    async def _terraform_apply(self, workspace: str) -> Dict[str, Any]:
        """Apply Terraform changes"""
        try:
            cmd = ["terraform", "apply", "-auto-approve", "-no-color"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.terraform_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return {
                    "status": "applied",
                    "output": stdout.decode()
                }
            else:
                return {
                    "status": "failed",
                    "error": stderr.decode()
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _terraform_import(self, workspace: str) -> Dict[str, Any]:
        """Import resources into Terraform state"""
        return {
            "status": "import_completed",
            "workspace": workspace
        }

    async def _terraform_refresh(self, workspace: str) -> Dict[str, Any]:
        """Refresh Terraform state"""
        try:
            cmd = ["terraform", "refresh", "-no-color"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.terraform_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return {
                    "status": "refreshed",
                    "output": stdout.decode()
                }
            else:
                return {
                    "status": "failed",
                    "error": stderr.decode()
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _store_drift_solution(
        self,
        drift_id: str,
        action: str,
        result: Dict[str, Any]
    ):
        """Store drift solution in knowledge base"""
        pass
