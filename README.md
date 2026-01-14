# 🧽 Sponge - AI-Powered RCA with SRE & Security Automation

**Complete Root Cause Analysis Platform with Google SRE Toil Reduction & Enterprise Security Automation**

Sponge is a comprehensive, open-source operational automation platform that combines ML-powered log analysis with SRE automation (toil reduction, self-healing, SLO management) and enterprise security orchestration (JIT access, SOAR, compliance scanning).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Cross-Platform](https://img.shields.io/badge/platform-Mac%20%7C%20Windows%20%7C%20Linux-lightgrey)](https://github.com/BarQode/Sponge)
[![Tests](https://img.shields.io/badge/tests-48%20passing-brightgreen)](#testing)

---

## 🌟 What's New in v2.0

### 🚀 SRE Automation (Toil Reduction)
- **Toil Tracking** - Identify and measure manual, repetitive work (reduce from 60% to <50%)
- **Runbook Automation** - Self-healing systems with automated remediation
- **SLO Management** - Error budget tracking with symptom-based alerting
- **Self-Healing** - Automatic incident response without human intervention
- **Ticketing Integration** - Jira and ServiceNow integration

### 🔒 Security Automation
- **Just-in-Time Access** - ChatOps-enabled temporary access with auto-revocation
- **SOAR Playbooks** - Automated security incident response (5 predefined playbooks)
- **Compliance as Code** - SOC2, ISO27001, PCI-DSS scanning with auto-remediation
- **Threat Intelligence** - AbuseIPDB, VirusTotal integration with threat feeds

### 💻 Local Application
- **Cross-Platform** - Runs locally on Mac, Windows, and Linux
- **4 Operation Modes** - CLI, Monitoring, SOAP API, Training
- **Prometheus Integration** - Comprehensive metrics for all operations
- **No Cloud Required** - Works offline with local databases

---

## 📋 Table of Contents

- [Features Overview](#-features-overview)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
  - [Mac Installation](#macos-installation)
  - [Windows Installation](#windows-installation)
  - [Linux Installation](#linux-installation)
  - [Docker Installation](#docker-installation)
- [Quick Start](#-quick-start)
- [Operation Modes](#-operation-modes)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [Dependencies](#-dependencies)
- [Testing](#-testing)
- [Documentation](#-documentation)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Features Overview

### Core RCA Capabilities
- 🤖 **Hybrid ML Engine** - TensorFlow + PyTorch + Scikit-learn
- 🔍 **Intelligent Pattern Recognition** - Semantic log analysis with LSTM
- 📊 **Performance Analysis** - CPU, Memory, Latency, Zombie process detection
- 🌐 **Web Scraping** - Automatic solution discovery from technical sources
- 💾 **Enhanced Knowledge Base** - Searchable fix repository with filtering and export

### SRE Automation Features
- ⚙️ **Toil Tracking System** - Identify repetitive work with automation scoring
- 📖 **Runbook Automation** - 4+ predefined runbooks for common issues
- 📉 **SLO Error Budgets** - Burn rate calculation and budget tracking
- 🔄 **Self-Healing Systems** - Auto-remediation with cooldown periods
- 🎫 **Ticketing Integration** - Jira and ServiceNow APIs

### Security Automation Features
- 🔐 **JIT Access Control** - Temporary access with Slack approval workflows
- 🛡️ **SOAR Engine** - 5 automated security playbooks
- ✅ **Compliance Scanner** - AWS resource scanning with auto-remediation
- 🕵️ **Threat Intelligence** - IP/domain/file reputation checking
- 🔒 **Audit Trails** - Complete access and security event logging

### Monitoring & Integration
- 📊 **Prometheus Metrics** - 40+ metrics for all operations
- 🔌 **SOAP API** - Enterprise SaaS integration
- ☁️ **Multi-Cloud** - AWS, Azure, GCP support
- 🐳 **Containerized** - Docker and Kubernetes ready

---

## 💻 System Requirements

### Minimum Requirements
| Component | Mac | Windows | Linux |
|-----------|-----|---------|-------|
| **OS** | macOS 10.15+ | Windows 10+ | Ubuntu 20.04+, CentOS 8+ |
| **Python** | 3.9+ | 3.9+ | 3.9+ |
| **RAM** | 4 GB | 4 GB | 4 GB |
| **Disk** | 2 GB | 2 GB | 2 GB |
| **CPU** | 2 cores | 2 cores | 2 cores |

### Recommended Requirements
- **OS**: Latest stable version
- **Python**: 3.10 or 3.11
- **RAM**: 8 GB+
- **Disk**: 10 GB+ SSD
- **CPU**: 4+ cores
- **Internet**: Required for SOAP API, threat intelligence, web scraping (optional for offline use)

---

## 🚀 Installation

### macOS Installation

#### Prerequisites
- **Homebrew** (optional): `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- **Python 3.9+**: `brew install python@3.10` (or download from [python.org](https://www.python.org/downloads/))

#### Installation Steps

```bash
# 1. Install Python (if not already installed)
brew install python@3.10

# 2. Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# 3. Create virtual environment
python3 -m venv venv

# 4. Activate virtual environment
source venv/bin/activate

# 5. Upgrade pip
pip install --upgrade pip

# 6. Install dependencies
pip install -r requirements.txt

# 7. Verify installation
python sponge_app.py --help
```

#### Running on Mac

```bash
# Activate virtual environment (always do this first)
source venv/bin/activate

# Run in CLI mode (interactive)
python sponge_app.py --mode cli

# Run in monitoring mode (continuous)
python sponge_app.py --mode monitor

# Run SOAP API server
python sponge_app.py --mode soap

# Run ML training
python sponge_app.py --mode training
```

---

### Windows Installation

#### Prerequisites

1. **Install Python 3.9+**
   - Download from [python.org](https://www.python.org/downloads/)
   - ✅ **IMPORTANT**: Check "Add Python to PATH" during installation
   - Click "Install Now"

2. **Install Git**
   - Download from [git-scm.com](https://git-scm.com/download/win)
   - Use default settings

#### Installation Steps (PowerShell)

```powershell
# 1. Open PowerShell as Administrator (optional but recommended)
# Right-click PowerShell → Run as Administrator

# 2. Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# 3. Create virtual environment
python -m venv venv

# 4. Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 5. Upgrade pip
python -m pip install --upgrade pip

# 6. Install dependencies
pip install -r requirements.txt

# 7. Verify installation
python sponge_app.py --help
```

#### Running on Windows

```powershell
# Activate virtual environment (always do this first)
.\venv\Scripts\Activate.ps1

# Run in CLI mode (interactive)
python sponge_app.py --mode cli

# Run in monitoring mode (continuous)
python sponge_app.py --mode monitor

# Run SOAP API server
python sponge_app.py --mode soap

# Run ML training
python sponge_app.py --mode training
```

#### Windows Troubleshooting

**Issue: "python is not recognized"**
```powershell
# Solution: Add Python to PATH manually
# 1. Search for "Environment Variables" in Windows
# 2. Edit "Path" variable
# 3. Add: C:\Users\YourName\AppData\Local\Programs\Python\Python310
# 4. Add: C:\Users\YourName\AppData\Local\Programs\Python\Python310\Scripts
# 5. Restart PowerShell
```

**Issue: Script execution disabled**
```powershell
# Solution: Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Linux Installation

#### Ubuntu/Debian

```bash
# 1. Update system packages
sudo apt update
sudo apt upgrade -y

# 2. Install Python 3.10+ and dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip git

# 3. Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# 4. Create virtual environment
python3 -m venv venv

# 5. Activate virtual environment
source venv/bin/activate

# 6. Upgrade pip
pip install --upgrade pip

# 7. Install dependencies
pip install -r requirements.txt

# 8. Verify installation
python sponge_app.py --help
```

#### CentOS/RHEL/Fedora

```bash
# 1. Install Python 3.10+
sudo yum install -y python310 python310-pip git

# OR for Fedora:
# sudo dnf install -y python3.10 python3-pip git

# 2-8. Follow same steps as Ubuntu above
```

#### Running on Linux

```bash
# Activate virtual environment
source venv/bin/activate

# Run in CLI mode
python sponge_app.py --mode cli

# Run in monitoring mode
python sponge_app.py --mode monitor

# Run SOAP API server
python sponge_app.py --mode soap
```

#### Run as Systemd Service (Optional)

Create `/etc/systemd/system/sponge-monitor.service`:

```ini
[Unit]
Description=Sponge RCA Tool - Monitoring Mode
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/Sponge
Environment="PATH=/home/your_username/Sponge/venv/bin"
ExecStart=/home/your_username/Sponge/venv/bin/python sponge_app.py --mode monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sponge-monitor
sudo systemctl start sponge-monitor
sudo systemctl status sponge-monitor

# View logs
journalctl -u sponge-monitor -f
```

---

### Docker Installation

#### Build Docker Image

```bash
# Clone repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# Build complete image (all features)
docker build -f Dockerfile.complete -t sponge:latest .

# OR build SOAP-only image (lighter)
docker build -f Dockerfile.soap -t sponge-soap:latest .
```

#### Run with Docker

```bash
# Run in CLI mode (interactive)
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  sponge:latest

# Run in monitoring mode (background)
docker run -d --name sponge-monitor \
  -p 9090:9090 \
  -v $(pwd)/data:/app/data \
  -e SPONGE_MODE=monitor \
  sponge:latest

# Run SOAP API server
docker run -d --name sponge-soap \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  -e SPONGE_MODE=soap \
  sponge:latest

# View logs
docker logs -f sponge-monitor
```

#### Run with Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.soap.yml up -d

# Services started:
# - sponge-soap (port 8001)
# - sponge-monitor (continuous monitoring)
# - sponge-ml (ML training on-demand)
# - sponge-certbot (certificate renewal)
# - sponge-scanner (vulnerability scanning)

# View logs
docker-compose -f docker-compose.soap.yml logs -f

# Stop all services
docker-compose -f docker-compose.soap.yml down
```

---

## ⚡ Quick Start

### 1. Install (Choose Your Platform)

```bash
# Mac/Linux
git clone https://github.com/BarQode/Sponge.git
cd Sponge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell)
git clone https://github.com/BarQode/Sponge.git
cd Sponge
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run Interactive CLI

```bash
python sponge_app.py --mode cli
```

You'll see:
```
============================================================
  Sponge RCA Tool - Interactive CLI
============================================================

Available commands:
  1. Train ML model
  2. Scrape data from URL
  3. Query knowledge base
  4. Track toil task
  5. Execute runbook
  6. Check SLO status
  7. Request JIT access
  8. Scan compliance
  9. Check threat intelligence
  0. Exit

Enter command number:
```

### 3. Try Monitoring Mode

```bash
python sponge_app.py --mode monitor
```

This will:
- ✅ Check SLOs and auto-heal issues
- ✅ Revoke expired access grants
- ✅ Update Prometheus metrics
- ✅ Monitor system health (CPU, memory, disk)

Metrics available at: http://localhost:9090/metrics

---

## 🎮 Operation Modes

### 1. CLI Mode (Interactive)

**Best for**: Learning, testing, manual operations

```bash
python sponge_app.py --mode cli
```

**Features:**
- Interactive menu with 9 commands
- Train ML model
- Query knowledge base
- Track toil tasks
- Execute runbooks
- Check SLO status
- Request JIT access
- Scan compliance
- Check threat intelligence

---

### 2. Monitoring Mode (Continuous)

**Best for**: Production, 24/7 operations

```bash
python sponge_app.py --mode monitor
```

**What it does:**
- Checks SLOs every 60 seconds
- Auto-remediates issues via runbooks
- Revokes expired access grants automatically
- Updates Prometheus metrics
- Monitors system resources

**Prometheus metrics on**: http://localhost:9090/metrics

---

### 3. SOAP API Mode

**Best for**: SaaS integration, remote access

```bash
python sponge_app.py --mode soap
```

**API available at:**
- Endpoint: http://localhost:8001
- WSDL: http://localhost:8001/?wsdl

**Features:**
- 7 SOAP endpoints for enterprise integration
- Knowledge base access
- Auto-remediation triggers
- Vulnerability scanning
- Certificate management

See [SOAP_API_GUIDE.md](docs/SOAP_API_GUIDE.md) for details.

---

### 4. Training Mode

**Best for**: ML model training with custom data

```bash
python sponge_app.py --mode training --data-source data.csv
```

**What it does:**
- Imports data from CSV/Excel/Parquet
- Trains hybrid ML model (TensorFlow + PyTorch)
- Saves trained model
- Reports accuracy metrics

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# API Keys (Optional)
ABUSEIPDB_API_KEY=your_api_key_here
VIRUSTOTAL_API_KEY=your_api_key_here

# Slack Integration (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# AWS Credentials (for compliance scanning)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Jira Integration (Optional)
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=PROJ

# ServiceNow Integration (Optional)
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your_username
SERVICENOW_PASSWORD=your_password

# Prometheus
PROMETHEUS_PORT=9090

# Database Paths (uses data/ by default)
TOIL_DB_PATH=data/toil_tracking.db
SLO_DB_PATH=data/slo_tracking.db
```

### Configuration File

Create `config.yaml` (optional):

```yaml
app:
  name: Sponge RCA Tool
  version: 2.0.0
  log_level: INFO

sre:
  toil_tracking:
    enabled: true
    min_pattern_occurrences: 3

  runbook_automation:
    enabled: true
    dry_run: false

  slo_management:
    enabled: true
    default_window_days: 30

security:
  jit_access:
    enabled: true
    slack_notifications: true

  compliance:
    enabled: true
    auto_remediate: true
    standards: [SOC2, ISO27001]

  threat_intelligence:
    enabled: true
    cache_ttl_hours: 24

monitoring:
  prometheus:
    enabled: true
    port: 9090
```

---

## 📚 Usage Examples

### Example 1: Track and Automate Toil

```bash
# Start CLI
python sponge_app.py --mode cli

# Select: 4. Track toil task
# Input:
# - Task ID: JIRA-123
# - Title: Manually restart stuck containers
# - Category: restart
# - Time spent: 0.5 hours

# The system will:
# ✅ Track the task
# ✅ Identify it as repetitive
# ✅ Suggest automation (runbook)
# ✅ Calculate potential time savings
```

### Example 2: Execute Runbook for Disk Cleanup

```bash
# Start CLI
python sponge_app.py --mode cli

# Select: 5. Execute runbook
# Choose: disk_cleanup

# The runbook will:
# ✅ Check disk usage
# ✅ Clean Docker images
# ✅ Clean old logs
# ✅ Verify space recovered
```

### Example 3: Request Temporary Access

```bash
# Start CLI
python sponge_app.py --mode cli

# Select: 7. Request JIT access
# Input:
# - Username: john.doe
# - Resource: prod-db
# - Permission: read
# - Duration: 60 minutes
# - Reason: Debug production issue

# The system will:
# ✅ Create access request
# ✅ Send Slack notification to approvers
# ✅ Grant access upon approval
# ✅ Auto-revoke after 60 minutes
```

### Example 4: Scan Compliance

```bash
# Start CLI
python sponge_app.py --mode cli

# Select: 8. Scan compliance
# The system will:
# ✅ Scan AWS S3 buckets
# ✅ Check for public access
# ✅ Check encryption status
# ✅ Auto-remediate CRITICAL violations
# ✅ Generate compliance score
```

### Example 5: Original RCA Usage

```bash
# Analyze application logs
python main.py --mode errors --source file --file app.log

# Performance analysis
python main.py --mode performance --integration mock

# View knowledge base stats
python main.py --stats

# Export knowledge base
python main.py --export results.csv
```

---

## 📦 Dependencies

All dependencies are automatically installed via `requirements.txt`. Here's what's included:

### Core ML & Data Processing
```
tensorflow>=2.15.0,<3.0.0
torch>=2.0.0
numpy>=1.24.0,<2.0.0
pandas>=2.0.0
scikit-learn>=1.3.0
```

### Web Scraping & HTTP
```
duckduckgo-search>=4.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
selenium>=4.15.0
lxml>=4.9.0
```

### SOAP & Enterprise Integration
```
spyne>=2.14.0
zeep>=4.2.1
```

### SRE & Automation
```
pyyaml>=6.0.0          # Ansible playbooks
psutil>=5.9.0          # System monitoring
ansible>=8.0.0         # Configuration management
docker>=6.1.0          # Container management
certbot>=2.7.0         # Certificate automation
```

### Monitoring
```
prometheus-client>=0.19.0
```

### Cloud Platforms
```
boto3>=1.28.0          # AWS integration
botocore>=1.31.0
```

### Data Formats
```
openpyxl>=3.1.0        # Excel support
pyarrow>=14.0.0        # Parquet support
tabulate>=0.9.0        # Table formatting
```

### Development & Testing
```
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

### Build Tools
```
pyinstaller>=6.0.0
setuptools>=68.0.0
wheel>=0.41.0
```

**Total**: ~30 dependencies

---

## 🧪 Testing

### Run All Tests

```bash
# Activate virtual environment first
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\Activate.ps1  # Windows

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_sre_and_security.py -v

# Run specific test class
pytest tests/test_sre_and_security.py::TestToilTracker -v
```

### Test Coverage

**48 comprehensive tests** covering:
- ✅ ToilTracker (6 tests)
- ✅ RunbookEngine/Executor (5 tests)
- ✅ SLOManager (4 tests)
- ✅ JITAccessManager (6 tests)
- ✅ SOAREngine (4 tests)
- ✅ ThreatIntelligence (5 tests)
- ✅ SelfHealingSystem (4 tests)
- ✅ PrometheusMetrics (8 tests)
- ✅ Integration tests (2 tests)
- ✅ Error handling (4 tests)

**All tests passing** ✅

---

## 📖 Documentation

### Complete Guides
- **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation for all platforms
- **[SOAP_API_GUIDE.md](docs/SOAP_API_GUIDE.md)** - Complete SOAP API documentation
- **[ARCHITECTURE_AND_COST_ANALYSIS.md](docs/ARCHITECTURE_AND_COST_ANALYSIS.md)** - System architecture

### Quick References
- **SRE Automation**: See [src/sre_automation/](src/sre_automation/)
- **Security Automation**: See [src/security_automation/](src/security_automation/)
- **ML Engine**: See [src/ml_engine.py](src/ml_engine.py)

### API Documentation

**Prometheus Metrics**: http://localhost:9090/metrics

**SOAP API WSDL**: http://localhost:8001/?wsdl

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: Module not found

```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\Activate.ps1  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### Issue: Permission denied (Mac/Linux)

```bash
# Solution: Make script executable
chmod +x sponge_app.py
chmod +x main.py
```

#### Issue: Port already in use

```bash
# Solution: Change port
python sponge_app.py --mode monitor --port 9091

# Or kill existing process
lsof -ti:9090 | xargs kill  # Mac/Linux
netstat -ano | findstr :9090  # Windows (find PID, then taskkill)
```

#### Issue: Database locked

```bash
# Solution: Stop all running instances
pkill -f sponge_app.py  # Mac/Linux
taskkill /F /IM python.exe  # Windows

# Remove lock files
rm data/*.db-shm data/*.db-wal
```

#### Issue: AWS credentials not found

```bash
# Solution 1: Configure AWS CLI
aws configure

# Solution 2: Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Solution 3: Add to .env file
echo "AWS_ACCESS_KEY_ID=your_key" >> .env
echo "AWS_SECRET_ACCESS_KEY=your_secret" >> .env
```

#### Issue: TensorFlow/PyTorch installation fails

```bash
# Mac with M1/M2 chip
pip install tensorflow-macos
pip install tensorflow-metal

# Windows with GPU
pip install tensorflow[and-cuda]

# Linux with GPU
pip install tensorflow[and-cuda]

# CPU-only (all platforms)
pip install tensorflow-cpu
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/BarQode/Sponge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/BarQode/Sponge/discussions)
- **Documentation**: [Wiki](https://github.com/BarQode/Sponge/wiki)

---

## 📁 Project Structure

```
Sponge/
├── src/
│   ├── sre_automation/          # SRE automation modules
│   │   ├── toil_tracker.py      # Toil identification
│   │   ├── runbook_automation.py # Self-healing runbooks
│   │   ├── slo_manager.py       # SLO & error budgets
│   │   ├── self_healing.py      # Auto-remediation
│   │   └── ticketing_integration.py # Jira/ServiceNow
│   ├── security_automation/     # Security modules
│   │   ├── jit_access.py        # JIT access control
│   │   ├── soar_engine.py       # SOAR playbooks
│   │   ├── compliance_scanner.py # Compliance scanning
│   │   └── threat_intelligence.py # Threat feeds
│   ├── soap_integration/        # SOAP API
│   ├── analyzers/               # Performance analyzers
│   ├── integrations/            # Platform integrations
│   ├── knowledge_base/          # Enhanced KB
│   ├── ml_training/             # ML training pipeline
│   ├── ml_engine.py             # Original ML clustering
│   ├── scraper.py               # Web scraping
│   ├── storage.py               # Data storage
│   └── prometheus_integration.py # Metrics
├── tests/
│   ├── test_sre_and_security.py # SRE & security tests
│   └── test_*.py                # Other test files
├── data/                        # Local databases
├── docs/                        # Documentation
├── kubernetes/                  # K8s manifests (optional)
├── terraform/                   # IaC (optional)
├── sponge_app.py               # Main app runner
├── main.py                      # Original RCA CLI
├── requirements.txt             # Dependencies
├── Dockerfile.complete          # Complete Docker image
├── Dockerfile.soap              # SOAP-only image
├── docker-compose.soap.yml      # Multi-service compose
├── INSTALLATION.md              # Installation guide
└── README.md                    # This file
```

---

## 🎯 Use Cases

### DevOps Teams
✅ Automated log analysis in CI/CD
✅ Performance monitoring
✅ Runbook automation for common issues
✅ Toil reduction tracking

### SRE Teams
✅ Proactive issue detection
✅ SLO management with error budgets
✅ Self-healing incident response
✅ Symptom-based alerting

### Security Teams
✅ JIT access control with auto-revocation
✅ Automated security incident response
✅ Compliance as code (SOC2, ISO27001)
✅ Threat intelligence integration

### Developers
✅ Local debugging with ML insights
✅ Performance optimization
✅ Learning from error patterns

---

## 🚀 What Makes Sponge Unique

| Feature | Sponge | Traditional Tools |
|---------|--------|-------------------|
| **Toil Reduction** | ✅ Automated tracking & scoring | ❌ Manual tracking |
| **Self-Healing** | ✅ Runbook automation | ❌ Manual intervention |
| **SLO Alerts** | ✅ Symptom-based (error budget) | ❌ Cause-based |
| **JIT Access** | ✅ Auto-revocation | ❌ Manual cleanup |
| **Compliance** | ✅ Auto-remediation | ❌ Manual fixes |
| **Threat Intel** | ✅ Automated blocking | ❌ Manual review |
| **Local First** | ✅ Runs on Mac/Win/Linux | ❌ Cloud-only |
| **Open Source** | ✅ 100% Free (MIT) | ❌ Expensive licenses |

---

## 📊 Performance Metrics

- **Logs analyzed per second**: ~1,000
- **Memory usage**: ~500MB base
- **Startup time**: <5 seconds
- **ML inference time**: <100ms per log
- **Runbook execution**: <30 seconds average
- **SLO calculation**: <1 second
- **Compliance scan**: <2 minutes (AWS account)

---

## 🔒 Security & Privacy

✅ **No telemetry** - Zero data collection
✅ **Local databases** - SQLite, no cloud storage
✅ **API keys local** - Stored in .env only
✅ **Audit trails** - Complete logging of all actions
✅ **Open source** - Full code transparency

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Submit pull requests
- ⭐ Star the project

### Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/Sponge.git
cd Sponge

# Create branch
git checkout -b feature/amazing-feature

# Install dev dependencies
pip install -r requirements.txt

# Make changes and test
pytest tests/ -v

# Commit and push
git commit -m "Add amazing feature"
git push origin feature/amazing-feature
```

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**Free to use, modify, and distribute - even commercially!** 🎉

---

## 🙏 Acknowledgments

- **TensorFlow** and **PyTorch** teams
- **Google SRE** book for toil reduction principles
- **Open Policy Agent** for compliance inspiration
- **DuckDuckGo** for search API
- **Open-source community** for support

---

## 🌟 Star History

If you find this project useful, please give it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=BarQode/Sponge&type=Date)](https://star-history.com/#BarQode/Sponge&Date)

---

## 📞 Support & Community

- **Issues**: [Report bugs](https://github.com/BarQode/Sponge/issues)
- **Discussions**: [Ask questions](https://github.com/BarQode/Sponge/discussions)
- **Documentation**: [Read the docs](https://github.com/BarQode/Sponge/wiki)

---

## 🔮 Roadmap

### v2.1 (Planned)
- [ ] Web UI dashboard (React)
- [ ] Real-time log streaming
- [ ] Plugin system for custom analyzers
- [ ] Mobile app for alerts

### v2.2 (Future)
- [ ] Multi-language support
- [ ] Additional ML models (BERT, GPT)
- [ ] More integrations (Prometheus, Loki)
- [ ] Automated remediation learning

---

## 💡 Quick Tips

**Tip 1**: Start with CLI mode to learn the features interactively
**Tip 2**: Run monitoring mode in background for 24/7 operations
**Tip 3**: Configure API keys in .env for full functionality
**Tip 4**: Use Docker for easier deployment
**Tip 5**: Check Prometheus metrics for observability

---

## 📈 Stats

- **7,609 lines** of production code
- **48 tests** (100% passing)
- **16 modules** (SRE + Security)
- **4 operation modes** (CLI, Monitor, SOAP, Training)
- **3 platforms** (Mac, Windows, Linux)
- **10+ integrations** (Jira, ServiceNow, Slack, AWS, etc.)

---

**Built with ❤️ for the DevOps, SRE, and Security community**

**100% Free and Open Source - Forever!** 🎉

---

## ⚡ TL;DR - Get Started in 3 Minutes

```bash
# 1. Install (Mac/Linux)
git clone https://github.com/BarQode/Sponge.git && cd Sponge
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Run
python sponge_app.py --mode cli

# 3. Explore
# Try the interactive menu to explore all features!
```

**That's it!** You're ready to reduce toil, automate security, and analyze root causes with ML. 🚀
