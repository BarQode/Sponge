# Sponge - MCP Agent Framework for Kubernetes Incident Response

## Architecture Overview

Sponge is an **Model Context Protocol (MCP) agent framework** designed to automatically detect, analyze, and remediate incidents in Kubernetes clusters and cloud workloads.

## Core Purpose

Deploy autonomous MCP agents that:
1. **Detect** - Monitor Kubernetes clusters for critical incidents
2. **Analyze** - Use ML/AI to determine root cause
3. **Remediate** - Automatically fix issues without human intervention
4. **Learn** - Store solutions in knowledge base for future use

## Target Incidents

### 1. Out-of-Memory (OOM) Errors
- Detect OOM kills in pods
- Analyze memory usage patterns
- Auto-scale resources or restart pods
- Adjust resource limits/requests

### 2. Codebase Failures
- Detect application crashes
- Analyze crash dumps and logs
- Rollback deployments if needed
- Apply hotfixes from knowledge base

### 3. Dependency Vulnerabilities
- Scan container images for CVEs
- Detect vulnerable dependencies
- Auto-patch or upgrade dependencies
- Block vulnerable deployments

### 4. Security Vulnerabilities
- Detect security misconfigurations
- Scan for RBAC issues
- Identify exposed secrets
- Auto-remediate security gaps

### 5. Terraform Drift
- Detect infrastructure drift
- Compare actual vs desired state
- Auto-apply Terraform corrections
- Prevent manual changes

## MCP Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Sponge MCP Framework                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  OOM Agent │  │  Security  │  │  Terraform │            │
│  │            │  │   Agent    │  │    Agent   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │Dependency  │  │  Codebase  │  │ Knowledge  │            │
│  │   Agent    │  │   Agent    │  │    Base    │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│              MCP Protocol Layer (Tools & Resources)          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Kubernetes API  │  Prometheus  │  Container Registry       │
│  Terraform State │  Git Repos   │  Secret Stores           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## MCP Agents

### OOM Detection Agent
**Capabilities:**
- Monitor pod memory metrics via Prometheus
- Detect OOM kills from Kubernetes events
- Analyze memory trends and predict OOMs
- Auto-remediate:
  - Increase memory limits
  - Scale horizontally
  - Restart stuck pods
  - Trigger alerts

**MCP Tools:**
- `detect_oom` - Scan for OOM events
- `analyze_memory` - Memory usage analysis
- `remediate_oom` - Auto-fix OOM issues
- `adjust_resources` - Update resource limits

### Dependency Vulnerability Agent
**Capabilities:**
- Scan container images with Trivy/Grype
- Check dependencies against CVE databases
- Analyze SBOM (Software Bill of Materials)
- Auto-remediate:
  - Update vulnerable packages
  - Rebuild images with patches
  - Block vulnerable deployments

**MCP Tools:**
- `scan_image` - Container image scanning
- `check_dependencies` - Dependency analysis
- `patch_vulnerability` - Auto-patch CVEs
- `block_deployment` - Prevent vulnerable deploys

### Security Vulnerability Agent
**Capabilities:**
- Scan for security misconfigurations
- Check RBAC policies
- Detect exposed secrets
- Audit network policies
- Auto-remediate:
  - Fix RBAC issues
  - Rotate exposed secrets
  - Apply security policies

**MCP Tools:**
- `scan_security` - Security configuration scan
- `check_rbac` - RBAC analysis
- `detect_secrets` - Secret exposure detection
- `remediate_security` - Auto-fix security issues

### Terraform Drift Agent
**Capabilities:**
- Compare Terraform state vs actual infrastructure
- Detect manual changes to resources
- Analyze drift impact
- Auto-remediate:
  - Apply Terraform corrections
  - Revert manual changes
  - Update state files

**MCP Tools:**
- `detect_drift` - Terraform drift detection
- `analyze_drift` - Drift impact analysis
- `apply_correction` - Auto-apply fixes
- `lock_resources` - Prevent manual changes

### Codebase Failure Agent
**Capabilities:**
- Detect application crashes
- Analyze crash dumps
- Check for known issues
- Auto-remediate:
  - Rollback deployments
  - Apply hotfixes
  - Restart services

**MCP Tools:**
- `detect_crash` - Application crash detection
- `analyze_crash` - Crash dump analysis
- `rollback_deployment` - Auto-rollback
- `apply_hotfix` - Deploy fixes

## Kubernetes Deployment

### Deployment Method
- **Helm Chart** - Standard Kubernetes deployment
- **Operator Pattern** - Custom resource definitions (CRDs)
- **DaemonSet** - Agent on every node (for monitoring)
- **Deployment** - Central control plane

### Components
```yaml
sponge/
├── control-plane/          # Central orchestration
│   ├── mcp-server          # MCP protocol server
│   ├── api-server          # REST API
│   └── knowledge-base      # Solution storage
│
├── agents/                 # MCP agents
│   ├── oom-agent
│   ├── security-agent
│   ├── dependency-agent
│   ├── terraform-agent
│   └── codebase-agent
│
├── collectors/             # Data collection
│   ├── metrics-collector   # Prometheus integration
│   ├── log-collector       # Log aggregation
│   └── event-collector     # Kubernetes events
│
└── knowledge-base/         # Solution database
    ├── postgresql          # Structured data
    └── vector-db           # ML embeddings
```

## Knowledge Base

### Solution Storage
- **Incident Type** - Category of issue
- **Root Cause** - Analysis results
- **Solution** - Remediation steps
- **Success Rate** - Effectiveness tracking
- **Similar Incidents** - Vector similarity search

### Learning Loop
1. Detect incident
2. Search knowledge base for similar issues
3. Apply known solution OR analyze new issue
4. Store new solution
5. Improve over time

## Installation

### Prerequisites
- Kubernetes 1.24+
- Helm 3.x
- Prometheus (optional but recommended)
- Terraform (for drift detection)

### Quick Install
```bash
# Add Helm repository
helm repo add sponge https://barqode.github.io/sponge

# Install Sponge with default configuration
helm install sponge sponge/sponge-mcp \
  --namespace sponge-system \
  --create-namespace

# Verify installation
kubectl get pods -n sponge-system
```

### Configuration
```yaml
# values.yaml
agents:
  oom:
    enabled: true
    autoRemediate: true
  security:
    enabled: true
    autoRemediate: false  # Require approval
  dependency:
    enabled: true
    scanInterval: "1h"
  terraform:
    enabled: true
    stateBackend: "s3"
    
knowledgeBase:
  storage: "postgresql"
  persistence: true
  size: "10Gi"

monitoring:
  prometheus:
    enabled: true
    scrapeInterval: "30s"
```

## MCP Protocol Integration

### MCP Server
Each agent exposes MCP-compatible tools:

```json
{
  "tools": [
    {
      "name": "detect_oom",
      "description": "Detect OOM events in Kubernetes cluster",
      "inputSchema": {
        "type": "object",
        "properties": {
          "namespace": {"type": "string"},
          "timeRange": {"type": "string"}
        }
      }
    }
  ]
}
```

### MCP Client
Agents can invoke each other's tools via MCP protocol

## Technology Stack

### Core
- **MCP Protocol** - Agent communication
- **Python 3.10+** - Primary language
- **Kubernetes Python Client** - K8s API interaction
- **gRPC** - Inter-agent communication

### Detection
- **Prometheus** - Metrics collection
- **Fluentd** - Log aggregation
- **Kubernetes Events** - Event monitoring

### Analysis
- **scikit-learn** - ML for pattern detection
- **TensorFlow** - Deep learning for anomaly detection
- **Vector DB (pgvector)** - Similarity search

### Remediation
- **Kubernetes API** - Resource updates
- **Helm** - Application management
- **Terraform** - Infrastructure changes

### Storage
- **PostgreSQL** - Relational data
- **Redis** - Caching
- **S3/Blob Storage** - Artifacts

## Next Steps

1. Implement MCP server framework
2. Build individual agents
3. Create Kubernetes manifests
4. Develop knowledge base
5. Test in production-like environment
6. Create comprehensive documentation
