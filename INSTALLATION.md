# Sponge RCA Tool - Installation Guide

## Complete Root Cause Analysis with SRE & Security Automation

Sponge is a comprehensive RCA tool that reduces operational toil through intelligent automation, ML-powered analysis, and security orchestration.

---

## Table of Contents

1. [Features](#features)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
   - [Mac Installation](#mac-installation)
   - [Windows Installation](#windows-installation)
   - [Linux Installation](#linux-installation)
   - [Docker Installation](#docker-installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Operation Modes](#operation-modes)
7. [Integrations](#integrations)
8. [Troubleshooting](#troubleshooting)

---

## Features

### SRE Automation (Toil Reduction)
- **Toil Tracking** - Identify and measure manual, repetitive work
- **Runbook Automation** - Self-healing systems with automated remediation
- **SLO-Based Alerting** - Symptom-based alerts with error budget tracking
- **Self-Healing** - Automatic incident response without human intervention
- **Ticketing Integration** - Jira and ServiceNow integration

### Security Automation
- **Just-in-Time (JIT) Access Control** - ChatOps-enabled temporary access with auto-revocation
- **SOAR Playbooks** - Automated security incident response
- **Compliance as Code** - Continuous compliance scanning (SOC2, ISO27001, PCI-DSS)
- **Threat Intelligence** - Integration with AbuseIPDB, VirusTotal, threat feeds

### ML & Data Processing
- **Hybrid ML Engine** - TensorFlow + PyTorch for RCA predictions
- **Web Scraping** - Extract operational data from various sources
- **Enhanced Knowledge Base** - Searchable fix repository with filtering and export

### Monitoring & Integration
- **Prometheus Metrics** - Comprehensive metrics for all operations
- **SOAP API** - Enterprise integration for SaaS applications
- **Multi-Cloud Support** - AWS, Azure, GCP integrations

---

## System Requirements

### Minimum Requirements
- **OS**: macOS 10.15+, Windows 10+, or Linux (Ubuntu 20.04+, CentOS 8+)
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 2 GB free space
- **Python**: 3.9 or higher
- **Internet**: Required for SOAP API, threat intelligence, and web scraping

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 10+ GB SSD
- **Python**: 3.10+

---

## Installation Methods

### Mac Installation

#### Option 1: Install from Source

```bash
# 1. Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify installation
python sponge_app.py --help
```

#### Option 2: Using Homebrew (if available)

```bash
# Install Python 3.10+ if needed
brew install python@3.10

# Follow Option 1 steps above
```

#### Running on Mac

```bash
# Activate virtual environment
source venv/bin/activate

# Run in CLI mode
python sponge_app.py --mode cli

# Run in monitoring mode (background)
python sponge_app.py --mode monitor

# Run SOAP API server
python sponge_app.py --mode soap
```

---

### Windows Installation

#### Prerequisites
1. Install **Python 3.9+** from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation
2. Install **Git** from [git-scm.com](https://git-scm.com/download/win)

#### Installation Steps

```powershell
# 1. Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify installation
python sponge_app.py --help
```

#### Running on Windows

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run in CLI mode
python sponge_app.py --mode cli

# Run in monitoring mode (background)
python sponge_app.py --mode monitor

# Run SOAP API server
python sponge_app.py --mode soap
```

---

### Linux Installation

#### Ubuntu/Debian

```bash
# 1. Update system and install Python
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3-pip git

# 2. Clone repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Verify installation
python sponge_app.py --help
```

#### CentOS/RHEL

```bash
# 1. Install Python 3.10+
sudo yum install -y python310 python310-pip git

# 2-5. Follow Ubuntu steps above
```

#### Running as a Service (systemd)

Create `/etc/systemd/system/sponge-monitor.service`:

```ini
[Unit]
Description=Sponge RCA Tool - Monitoring Mode
After=network.target

[Service]
Type=simple
User=sponge
WorkingDirectory=/opt/sponge
Environment="PATH=/opt/sponge/venv/bin"
ExecStart=/opt/sponge/venv/bin/python sponge_app.py --mode monitor
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
```

---

### Docker Installation

#### Build Docker Image

```bash
# Clone repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# Build complete image
docker build -f Dockerfile.complete -t sponge:latest .

# Or build SOAP-only image
docker build -f Dockerfile.soap -t sponge-soap:latest .
```

#### Run with Docker

```bash
# Run in CLI mode (interactive)
docker run -it --rm sponge:latest

# Run in monitoring mode
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
```

#### Run with Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.soap.yml up -d

# View logs
docker-compose -f docker-compose.soap.yml logs -f

# Stop all services
docker-compose -f docker-compose.soap.yml down
```

---

## Configuration

### Environment Variables

Create `.env` file in the project root:

```bash
# API Keys
ABUSEIPDB_API_KEY=your_api_key_here
VIRUSTOTAL_API_KEY=your_api_key_here

# Slack Integration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# AWS Credentials (for compliance scanning)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Jira Integration
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=PROJ

# ServiceNow Integration
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your_username
SERVICENOW_PASSWORD=your_password

# Prometheus
PROMETHEUS_PORT=9090

# Database Paths (optional, defaults to data/)
TOIL_DB_PATH=data/toil_tracking.db
SLO_DB_PATH=data/slo_tracking.db
JIT_ACCESS_DB_PATH=data/jit_access.db
SOAR_DB_PATH=data/soar_incidents.db
THREAT_INTEL_DB_PATH=data/threat_intelligence.db
```

### Configuration File

Create `config.yaml`:

```yaml
app:
  name: Sponge RCA Tool
  version: 2.0.0
  log_level: INFO

sre:
  toil_tracking:
    enabled: true
    auto_identify_patterns: true
    min_pattern_occurrences: 3

  runbook_automation:
    enabled: true
    dry_run: false
    max_execution_time: 600

  slo_management:
    enabled: true
    default_window_days: 30
    alert_threshold: 80

  self_healing:
    enabled: true
    cooldown_minutes: 5

security:
  jit_access:
    enabled: true
    default_max_duration: 60
    slack_notifications: true

  soar:
    enabled: true
    auto_execute_playbooks: true

  compliance:
    enabled: true
    auto_remediate: true
    standards:
      - SOC2
      - ISO27001
      - PCI-DSS

  threat_intelligence:
    enabled: true
    cache_ttl_hours: 24
    auto_import_feeds: true

ml:
  training:
    enabled: true
    batch_size: 32
    epochs: 100

monitoring:
  prometheus:
    enabled: true
    port: 9090

  metrics_update_interval: 60
```

---

## Running the Application

### CLI Mode (Interactive)

```bash
python sponge_app.py --mode cli
```

Interactive menu with options:
1. Train ML model
2. Scrape data from URL
3. Query knowledge base
4. Track toil task
5. Execute runbook
6. Check SLO status
7. Request JIT access
8. Scan compliance
9. Check threat intelligence

### Monitoring Mode (Continuous)

```bash
python sponge_app.py --mode monitor
```

Runs continuously:
- Monitors SLOs and auto-heals issues
- Revokes expired access grants
- Updates Prometheus metrics
- Checks compliance violations

### SOAP API Mode

```bash
python sponge_app.py --mode soap
```

Starts SOAP API server on port 8001:
- WSDL: http://localhost:8001/?wsdl
- Endpoints: See [SOAP_API_GUIDE.md](docs/SOAP_API_GUIDE.md)

### Training Mode

```bash
python sponge_app.py --mode training --data-source /path/to/data.csv
```

Trains ML model with provided data.

---

## Operation Modes

### Local Machine Operation

Sponge runs primarily as a **local application** on your Mac/Windows/Linux machine:

- **Data Storage**: Local SQLite databases in `data/` directory
- **Internet Access**: Used for:
  - SOAP API functionality
  - Web scraping
  - Threat intelligence lookups (AbuseIPDB, VirusTotal)
  - Slack notifications
  - Cloud compliance scanning (AWS)

- **Offline Capabilities**:
  - ML training and predictions
  - Knowledge base queries
  - Runbook execution (local commands)
  - Toil tracking
  - Most SRE automation features

### Hybrid Operation

- **Local**: ML training, knowledge base, toil tracking, runbook execution
- **Cloud**: Compliance scanning (AWS/Azure/GCP), threat intelligence
- **Network**: SOAP API for remote SaaS integration

---

## Integrations

### Ticketing Systems

#### Jira

```python
from src.sre_automation import JiraClient

jira = JiraClient(
    url="https://your-domain.atlassian.net",
    username="your-email@example.com",
    api_token="your_api_token",
    project_key="PROJ"
)

# Create ticket
ticket_id = jira.create_ticket(
    title="High memory usage detected",
    description="Memory usage exceeded 85%",
    priority="High",
    labels=["toil", "automation-candidate"]
)
```

#### ServiceNow

```python
from src.sre_automation import ServiceNowClient

snow = ServiceNowClient(
    instance_url="https://your-instance.service-now.com",
    username="your_username",
    password="your_password"
)

incident = snow.create_ticket(
    title="Database connection pool exhausted",
    description="Connection pool reached max capacity",
    priority="2"
)
```

### Prometheus Integration

```python
from src.prometheus_integration import get_metrics

metrics = get_metrics()

# Start metrics server
metrics.start_server_async()

# Metrics available at: http://localhost:9090/metrics
```

View metrics in Prometheus:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'sponge'
    static_configs:
      - targets: ['localhost:9090']
```

### Slack Integration

Set `SLACK_WEBHOOK_URL` in `.env` for:
- JIT access request notifications
- SLO alert notifications
- Security incident alerts

---

## Troubleshooting

### Common Issues

#### Issue: ModuleNotFoundError

```bash
# Solution: Ensure virtual environment is activated and dependencies installed
source venv/bin/activate  # Mac/Linux
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

#### Issue: Permission denied (Mac/Linux)

```bash
# Solution: Make scripts executable
chmod +x sponge_app.py
```

#### Issue: Port already in use

```bash
# Solution: Change port or kill existing process
python sponge_app.py --mode monitor --port 9091
```

#### Issue: Database locked

```bash
# Solution: Stop all running instances
pkill -f sponge_app.py
rm data/*.db-shm data/*.db-wal  # Remove lock files
```

#### Issue: AWS credentials not found (compliance scanning)

```bash
# Solution: Configure AWS credentials
aws configure
# Or set environment variables in .env
```

### Logs

Check logs for detailed error information:

```bash
# View recent logs
tail -f logs/sponge.log

# Search for errors
grep ERROR logs/sponge.log
```

### Getting Help

- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/BarQode/Sponge/issues
- **SOAP API Guide**: `docs/SOAP_API_GUIDE.md`

---

## Next Steps

1. **Configure API Keys**: Add AbuseIPDB, VirusTotal keys to `.env`
2. **Set Up Integrations**: Configure Slack, Jira, or ServiceNow
3. **Import Data**: Load your operational data for ML training
4. **Create Runbooks**: Define custom runbooks for your environment
5. **Define SLOs**: Set up SLOs for your services
6. **Enable Monitoring**: Run in monitoring mode for continuous operation

---

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Rotate credentials** regularly
4. **Enable MFA** for all integrated services
5. **Review audit logs** in `data/*.db` databases
6. **Limit JIT access** durations to minimum required
7. **Monitor compliance** scores regularly

---

## Performance Tuning

### For Large Datasets

```yaml
# config.yaml
ml:
  training:
    batch_size: 64  # Increase for more RAM
    workers: 4      # Parallel data loading

database:
  connection_pool_size: 10
  timeout: 30
```

### For High-Frequency Monitoring

```bash
# Reduce monitoring interval (default: 60s)
# Edit sponge_app.py: time.sleep(30)  # Check every 30 seconds
```

---

## License

See [LICENSE](LICENSE) file for details.

---

## Support

For enterprise support, custom integrations, or deployment assistance, contact the development team.
