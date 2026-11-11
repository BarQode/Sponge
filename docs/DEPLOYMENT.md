# Sponge MCP Agent Framework — Deployment Guide

## Overview

This guide covers deploying all Sponge MCP agents (including the new Log
Analysis Agent) to a Kubernetes cluster, configuring observability platform
credentials, and operating the framework day-to-day.

---

## Prerequisites

| Requirement | Minimum Version |
|---|---|
| Kubernetes | 1.24+ |
| Helm | 3.10+ |
| Python (for local dev) | 3.10+ |
| kubectl | 1.24+ |
| Terraform (drift agent) | 1.5+ (optional) |

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Sponge MCP Control Plane                        │
│  Namespace: sponge-system                                              │
├──────────────────┬─────────────────────────────────────────────────────┤
│  MCP Server      │  Agent Pods                                         │
│  (Deployment)    │                                                     │
│                  │  ┌──────────────────┐  ┌──────────────────────┐    │
│  Receives tool   │  │  Log Analysis    │  │  OOM Detection       │    │
│  invocations     │  │  Agent           │  │  Agent               │    │
│  from all agents │  │                  │  │                      │    │
│                  │  │  Dynatrace       │  │  K8s Events API      │    │
│                  │  │  CloudWatch      │  │  Prometheus          │    │
│                  │  │  Datadog         │  └──────────────────────┘    │
│                  │  │  Splunk …        │                              │
│                  │  └──────────────────┘  ┌──────────────────────┐    │
│                  │                        │  Security Agent      │    │
│                  │  ┌──────────────────┐  │  RBAC / Secrets      │    │
│                  │  │  Dependency      │  └──────────────────────┘    │
│                  │  │  Agent           │                              │
│                  │  │  Trivy / Grype   │  ┌──────────────────────┐    │
│                  │  └──────────────────┘  │  Terraform Agent     │    │
│                  │                        │  State drift         │    │
│                  │  ┌──────────────────┐  └──────────────────────┘    │
│                  │  │  Codebase Agent  │                              │
│                  │  │  Crash / loops   │                              │
│                  │  └──────────────────┘                             │
├──────────────────┴─────────────────────────────────────────────────────┤
│  Remediation Orchestrator (Deployment)                                 │
│  Receives → Queries KB → Deploys fix → Monitors → Escalates           │
├────────────────────────────────────────────────────────────────────────┤
│  Knowledge Base (StatefulSet: PostgreSQL + pgvector)                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Install via Helm

### Add the chart repository

```bash
helm repo add sponge https://barqode.github.io/sponge
helm repo update
```

### Minimal install (all agents, no platform credentials)

```bash
helm install sponge sponge/sponge-mcp \
  --namespace sponge-system \
  --create-namespace
```

### Full install with observability platforms

```bash
helm install sponge sponge/sponge-mcp \
  --namespace sponge-system \
  --create-namespace \
  --values my-values.yaml
```

---

## 2. Helm values reference

```yaml
# my-values.yaml

# ── Global ──────────────────────────────────────────────────────────────
global:
  image:
    repository: ghcr.io/barqode/sponge
    tag: "4.0.0"
  namespace: sponge-system

# ── MCP Server ──────────────────────────────────────────────────────────
mcpServer:
  replicas: 2
  port: 8765
  resources:
    requests: { cpu: "250m", memory: "256Mi" }
    limits:   { cpu: "1",    memory: "512Mi" }

# ── Agents ──────────────────────────────────────────────────────────────
agents:

  logAnalysis:
    enabled: true
    schedule: "*/5 * * * *"      # cron: how often to fetch & analyse
    lookbackMinutes: 60
    errorThreshold: 5            # occurrences before auto-remediate
    autoRemediate: true
    platforms:
      dynatrace:
        enabled: true
        apiToken: ""             # or use secretRef below
        environmentUrl: "https://XXXXX.live.dynatrace.com"
        # secretRef:
        #   name: sponge-dynatrace-secret
        #   key: api_token
      cloudwatch:
        enabled: true
        awsAccessKeyId: ""
        awsSecretAccessKey: ""
        awsRegion: "us-east-1"
        logGroupName: "/aws/eks/my-cluster"
      datadog:
        enabled: false
        apiKey: ""
        appKey: ""
        site: "datadoghq.com"
      splunk:
        enabled: false
        host: ""
        token: ""
        port: 8089
      grafana:
        enabled: false
        url: "http://grafana.monitoring.svc.cluster.local:3000"
        apiKey: ""
      elastic:
        enabled: false
        host: ""
        port: 9200
        username: ""
        password: ""
      sentry:
        enabled: false
        dsn: ""
      prometheus:
        enabled: true
        url: "http://prometheus.monitoring.svc.cluster.local:9090"

  oom:
    enabled: true
    autoRemediate: true
    memoryThreshold: 0.90

  dependency:
    enabled: true
    scanner: "trivy"             # trivy | grype
    blockCritical: true
    scanInterval: "1h"

  security:
    enabled: true
    autoRemediate: false         # requires human approval
    checkInterval: "1h"

  terraform:
    enabled: false               # enable when Terraform workspace is configured
    terraformDir: "/workspace/terraform"
    stateBackend: "s3"
    autoCorrect: false

  codebase:
    enabled: true
    autoRollback: true
    errorThreshold: 0.05

# ── Remediation Orchestrator ─────────────────────────────────────────────
remediationOrchestrator:
  enabled: true
  autoDeploy: true
  requireApproval: false         # set true for critical incidents
  escalationThreshold: 3        # failures before paging on-call

# ── Knowledge Base ───────────────────────────────────────────────────────
knowledgeBase:
  enabled: true
  storage: "postgresql"
  persistence: true
  size: "20Gi"
  storageClass: ""               # leave blank for default

# ── Notifications ────────────────────────────────────────────────────────
notifications:
  slack:
    enabled: false
    webhookUrl: ""
    channel: "#incidents"
  pagerduty:
    enabled: false
    integrationKey: ""

# ── RBAC ────────────────────────────────────────────────────────────────
rbac:
  create: true                   # creates ServiceAccount + ClusterRole
  serviceAccountName: sponge

# ── Prometheus metrics ───────────────────────────────────────────────────
metrics:
  enabled: true
  port: 9090
  scrapeInterval: "30s"
```

---

## 3. Storing credentials as Kubernetes Secrets

Never put API tokens directly in `values.yaml` for production. Create secrets
first and reference them:

```bash
# Dynatrace
kubectl create secret generic sponge-dynatrace \
  --from-literal=api_token="$DT_TOKEN" \
  -n sponge-system

# AWS CloudWatch
kubectl create secret generic sponge-aws \
  --from-literal=aws_access_key_id="$AWS_KEY" \
  --from-literal=aws_secret_access_key="$AWS_SECRET" \
  -n sponge-system

# Datadog
kubectl create secret generic sponge-datadog \
  --from-literal=api_key="$DD_API_KEY" \
  --from-literal=app_key="$DD_APP_KEY" \
  -n sponge-system
```

Then reference in `values.yaml`:

```yaml
agents:
  logAnalysis:
    platforms:
      dynatrace:
        secretRef:
          name: sponge-dynatrace
          key: api_token
```

---

## 4. RBAC requirements

The Sponge service account needs the following cluster-level permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: sponge-agent
rules:
  # Read pods, events, namespaces
  - apiGroups: [""]
    resources: ["pods", "pods/log", "events", "namespaces",
                "configmaps", "secrets", "nodes"]
    verbs: ["get", "list", "watch"]
  # Update deployments (for memory limit changes / rollbacks)
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "replicasets", "daemonsets"]
    verbs: ["get", "list", "watch", "update", "patch"]
  # Delete pods (for restarts)
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["delete"]
  # Read RBAC
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
    verbs: ["get", "list", "watch"]
  # Network policies
  - apiGroups: ["networking.k8s.io"]
    resources: ["networkpolicies"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
```

---

## 5. Local development / testing

```bash
# Clone
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/test_log_analysis_agent.py -v

# Run all tests
pytest tests/ -v

# Start the MCP server locally (connects to current kubeconfig context)
python -c "
import asyncio
from src.mcp.server import MCPServer
from src.agents.log_analysis_agent import LogAnalysisAgent

agent = LogAnalysisAgent(platform_configs={
    'prometheus': {'url': 'http://localhost:9090'}
})

server = MCPServer()
server.register_agent(agent.get_mcp_agent())
asyncio.run(server.start())
"
```

---

## 6. Configuring the Log Analysis Agent programmatically

```python
from src.agents.log_analysis_agent import LogAnalysisAgent
from src.agents.remediation_orchestrator import RemediationOrchestrator
from src.mcp.server import MCPServer

# Configure platforms
platform_configs = {
    "dynatrace": {
        "api_token": "YOUR_DT_TOKEN",
        "environment_url": "https://XXXXX.live.dynatrace.com",
    },
    "cloudwatch": {
        "aws_access_key_id": "...",
        "aws_secret_access_key": "...",
        "aws_region": "us-east-1",
        "log_group_name": "/aws/eks/prod-cluster",
    },
    "datadog": {
        "api_key": "...",
        "app_key": "...",
        "site": "datadoghq.com",
    },
    "splunk": {
        "host": "splunk.example.com",
        "token": "...",
        "port": 8089,
    },
}

# Build MCP server and register agents
server = MCPServer()

orchestrator = RemediationOrchestrator(auto_deploy=True)
server.register_agent(orchestrator.get_mcp_agent())

log_agent = LogAnalysisAgent(
    platform_configs=platform_configs,
    default_lookback_minutes=60,
    error_threshold=5,
    auto_remediate=True,
    mcp_server=server,          # wires log agent → orchestrator
)
server.register_agent(log_agent.get_mcp_agent())

# Start
import asyncio
asyncio.run(server.start())
```

---

## 7. MCP tool invocation examples

```bash
# Fetch last 30 minutes of Dynatrace errors
curl -X POST http://localhost:8765/tools/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "log-analysis-agent.fetch_logs",
    "arguments": {
      "platform": "dynatrace",
      "lookback_minutes": 30,
      "severity_filter": "ERROR"
    }
  }'

# Analyse errors across all platforms
curl -X POST http://localhost:8765/tools/invoke \
  -d '{"tool": "log-analysis-agent.analyze_errors", "arguments": {"top_n": 10}}'

# Cross-correlate signals
curl -X POST http://localhost:8765/tools/invoke \
  -d '{"tool": "log-analysis-agent.correlate_signals", "arguments": {"service": "payments"}}'

# Remediate a specific error fingerprint
curl -X POST http://localhost:8765/tools/invoke \
  -d '{
    "tool": "log-analysis-agent.remediate_error",
    "arguments": {"error_fingerprint": "a1b2c3d4e5f60001", "dry_run": false}
  }'
```

---

## 8. Knowledge base

Every successful remediation is automatically stored:

```json
{
  "fingerprint": "a1b2c3d4e5f60001",
  "finding": {
    "incident_type": "oom",
    "count": 7,
    "sources": ["dynatrace", "cloudwatch"],
    "sample_message": "OOMKilled container payments-api ..."
  },
  "solution_summary": "Increased memory limit from 256Mi to 384Mi",
  "actions_taken": ["memory_limit_increased", "deployment_restarted"],
  "success": true,
  "recorded_at": "2026-11-11T09:00:00Z",
  "agent": "log-analysis-agent"
}
```

On the next similar incident, the agent queries the knowledge base first and
applies the proven solution before attempting a new analysis.

---

## 9. Upgrading

```bash
helm repo update
helm upgrade sponge sponge/sponge-mcp \
  --namespace sponge-system \
  --values my-values.yaml
```

---

## 10. Uninstalling

```bash
helm uninstall sponge -n sponge-system
kubectl delete namespace sponge-system
```
