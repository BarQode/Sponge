# Sponge SOAP API Integration Guide

## Overview

The Sponge SOAP API provides enterprise integration capabilities for SaaS applications, enabling:
- **Auto-remediation** of detected issues
- **Vulnerability scanning** of running applications
- **Certificate management** and auto-renewal
- **Container lifecycle management**
- **Ansible-based automation** deployment

---

## 🚀 Quick Start

### Start SOAP API Server

```bash
# Using Docker
docker-compose -f docker-compose.soap.yml up -d sponge-soap

# Using Python directly
python -m src.soap_integration.soap_server
```

The SOAP API will be available at:
- **Endpoint:** `http://localhost:8001`
- **WSDL:** `http://localhost:8001/?wsdl`

---

## 📡 SOAP Endpoints

### 1. Get Fixes by Category

Retrieve all fixes for a specific category from knowledge base.

```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:spon="sponge.rca">
   <soapenv:Header/>
   <soapenv:Body>
      <spon:get_fixes_by_category>
         <spon:category>Memory</spon:category>
      </spon:get_fixes_by_category>
   </soapenv:Body>
</soapenv:Envelope>
```

**Response:**
```xml
<Fix>
    <error_pattern>Memory leak in application</error_pattern>
    <category>Memory</category>
    <severity>critical</severity>
    <solution>Restart service and clear caches</solution>
    <implementation_steps>["Step 1", "Step 2"]</implementation_steps>
    <confidence>0.95</confidence>
</Fix>
```

### 2. Get Critical Fixes

Retrieve critical fixes above confidence threshold.

```xml
<spon:get_critical_fixes>
    <spon:min_confidence>0.8</spon:min_confidence>
</spon:get_critical_fixes>
```

### 3. Auto-Remediate Issue

Automatically remediate a detected issue using Ansible.

```xml
<spon:auto_remediate>
    <spon:request>
        <spon:issue_id>memory_leak_001</spon:issue_id>
        <spon:environment>production</spon:environment>
        <spon:auto_approve>false</spon:auto_approve>
        <spon:notification_email>admin@example.com</spon:notification_email>
    </spon:request>
</spon:auto_remediate>
```

**Response:**
```xml
<RemediationResult>
    <request_id>REM-20240106120000</request_id>
    <status>success</status>
    <message>Remediation completed successfully</message>
    <ansible_playbook_path>/app/ansible_playbooks/remediate_Memory_20240106.yml</ansible_playbook_path>
    <timestamp>2024-01-06T12:00:00</timestamp>
</RemediationResult>
```

### 4. Scan Vulnerabilities

Scan environment for security vulnerabilities.

```xml
<spon:scan_vulnerabilities>
    <spon:target_environment>production</spon:target_environment>
</spon:scan_vulnerabilities>
```

### 5. Update Certificates

Auto-renew SSL/TLS certificates.

```xml
<spon:update_certificates>
    <spon:domain>example.com</spon:domain>
    <spon:cert_type>ssl</spon:cert_type>
</spon:update_certificates>
```

### 6. Restart Containers

Restart containers matching pattern.

```xml
<spon:restart_containers>
    <spon:container_pattern>app_*</spon:container_pattern>
</spon:restart_containers>
```

### 7. Health Check

```xml
<spon:health_check/>
```

---

## 🔧 Integration Examples

### Python Client

```python
from zeep import Client

# Create SOAP client
client = Client('http://localhost:8001/?wsdl')

# Get critical fixes
fixes = client.service.get_critical_fixes(min_confidence='0.8')

for fix in fixes:
    print(f"Issue: {fix.error_pattern}")
    print(f"Severity: {fix.severity}")
    print(f"Solution: {fix.solution}")

# Auto-remediate
from zeep import xsd

request = xsd.Element(
    '{sponge.rca}RemediationRequest',
    xsd.ComplexType([
        xsd.Element('{sponge.rca}issue_id', xsd.String()),
        xsd.Element('{sponge.rca}environment', xsd.String()),
        xsd.Element('{sponge.rca}auto_approve', xsd.String()),
    ])
)

remediation_request = request(
    issue_id='memory_leak_001',
    environment='staging',
    auto_approve='true'
)

result = client.service.auto_remediate(remediation_request)
print(f"Status: {result.status}")
```

### cURL Example

```bash
# Get WSDL
curl http://localhost:8001/?wsdl

# Call health check
curl -X POST http://localhost:8001/ \
  -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:spon="sponge.rca">
   <soapenv:Body>
      <spon:health_check/>
   </soapenv:Body>
</soapenv:Envelope>'
```

### Node.js Client

```javascript
const soap = require('soap');

const url = 'http://localhost:8001/?wsdl';

soap.createClient(url, function(err, client) {
    // Get fixes
    client.get_fixes_by_category({category: 'CPU'}, function(err, result) {
        console.log(result);
    });

    // Auto-remediate
    const request = {
        issue_id: 'high_cpu_001',
        environment: 'staging',
        auto_approve: 'true',
        notification_email: 'admin@example.com'
    };

    client.auto_remediate({request: request}, function(err, result) {
        console.log('Status:', result.status);
        console.log('Message:', result.message);
    });
});
```

---

## 🤖 Auto-Remediation Workflow

### 1. Issue Detection
- Monitoring system detects issue
- Issue logged to Sponge knowledge base

### 2. SOAP API Call
```python
# SaaS app calls SOAP API
result = client.service.auto_remediate(
    issue_id='detected_issue',
    environment='production',
    auto_approve=False  # Requires manual approval for prod
)
```

### 3. Ansible Playbook Generation
- Sponge generates Ansible playbook from knowledge base
- Playbook includes pre-checks, fixes, and post-checks

### 4. Approval (if required)
- Critical/production fixes require approval
- Integration with approval systems (ServiceNow, Jira, etc.)

### 5. Execution
- Ansible playbook executed on target hosts
- Dry-run performed first
- Actual execution with logging

### 6. Verification
- Post-check verifies fix applied
- Status reported back via SOAP

### 7. Notification
- Email/Slack notification sent
- Results logged to knowledge base

---

## 🔒 Security Features

### Vulnerability Scanning

Automatically scans for:
- Container image vulnerabilities (using Trivy)
- Dependency vulnerabilities (using Safety)
- Exposed secrets in configuration files
- Expiring SSL/TLS certificates
- Known CVEs
- Insecure configurations

### Certificate Management

- Auto-renewal using Let's Encrypt (certbot)
- Custom CA support for internal certificates
- Certificate expiry monitoring
- Automated policy updates

### Container Security

- Resource usage monitoring
- Automatic restart of overused containers
- Fresh container deployment
- Old image cleanup
- Security policy enforcement

---

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.soap.yml up -d

# Start specific services
docker-compose -f docker-compose.soap.yml up -d sponge-soap sponge-monitor

# View logs
docker-compose -f docker-compose.soap.yml logs -f sponge-soap

# Stop services
docker-compose -f docker-compose.soap.yml down
```

### Environment Variables

```bash
# SOAP API Configuration
SPONGE_MODE=soap              # Mode: soap, ml-training, monitor, cli
KB_FILE=/app/data/knowledge_base.xlsx
LOG_LEVEL=INFO

# Container Monitor
CPU_THRESHOLD=80              # CPU usage threshold (%)
MEMORY_THRESHOLD=85           # Memory usage threshold (%)
AUTO_RESTART=true             # Auto-restart overused containers

# Ansible Configuration
ANSIBLE_HOST_KEY_CHECKING=False
ANSIBLE_INVENTORY=/app/ansible/inventory
```

---

## 📊 Monitoring & Logging

### Health Checks

```bash
# Check SOAP API health
curl http://localhost:8001/?wsdl

# Check specific service health
docker-compose -f docker-compose.soap.yml ps
```

### View Logs

```bash
# SOAP API logs
docker logs -f sponge-soap-api

# Container monitor logs
docker logs -f sponge-monitor

# All services
docker-compose -f docker-compose.soap.yml logs -f
```

### Metrics

Monitor:
- SOAP API request count
- Remediation success rate
- Container restart frequency
- Vulnerability scan results
- Certificate expiry status

---

## 🔄 Ansible Integration

### Inventory Setup

Create inventory files for each environment:

**`ansible/inventory/production.ini`:**
```ini
[prod_servers]
web1.example.com
web2.example.com
db1.example.com

[prod_servers:vars]
ansible_user=deploy
ansible_python_interpreter=/usr/bin/python3
```

### Generated Playbook Example

```yaml
---
- name: Remediate Memory - Memory leak in application
  hosts: prod_servers
  become: true
  vars:
    environment: production
    issue_category: Memory
    severity: critical

  tasks:
    - name: Pre-check - Verify issue exists
      shell: free -m | awk '/Mem:/ {print $3/$2 * 100}'
      register: pre_check
      ignore_errors: true

    - name: Clear system caches
      shell: sync && echo 3 > /proc/sys/vm/drop_caches
      when: pre_check.stdout|float > 80

    - name: Restart high-memory services
      systemd:
        name: "{{ item }}"
        state: restarted
      loop:
        - application
        - cache-service
      ignore_errors: true

    - name: Post-check - Verify fix applied
      shell: free -m | awk '/Mem:/ {print $3/$2 * 100}'
      register: post_check
```

---

## 🧪 Testing

### Run Tests

```bash
# Run SOAP integration tests
pytest tests/test_soap_integration.py -v

# Run with coverage
pytest tests/test_soap_integration.py --cov=src.soap_integration --cov-report=html

# Test specific functionality
pytest tests/test_soap_integration.py::TestRemediationAgent -v
```

### Manual Testing

```bash
# Test SOAP endpoint
python3 << EOF
from zeep import Client
client = Client('http://localhost:8001/?wsdl')
print(client.service.health_check())
EOF
```

---

## 🚨 Troubleshooting

### SOAP API Not Starting

```bash
# Check logs
docker logs sponge-soap-api

# Verify port not in use
lsof -i :8001

# Test connectivity
curl -v http://localhost:8001/?wsdl
```

### Ansible Execution Fails

```bash
# Test Ansible connectivity
ansible -i ansible/inventory/production.ini all -m ping

# Run playbook manually
ansible-playbook -i ansible/inventory/production.ini \
                 ansible_playbooks/remediate_Memory_*.yml \
                 --check  # Dry run
```

### Docker Permission Issues

```bash
# Add user to docker group
sudo usermod -aG docker sponge

# Restart Docker service
sudo systemctl restart docker
```

---

## 📚 Best Practices

### 1. **Use Staging First**
Always test remediations in staging before production

### 2. **Require Approval for Critical**
Never auto-approve critical/production fixes

### 3. **Monitor Remediation Results**
Track success rate and adjust thresholds

### 4. **Keep Knowledge Base Updated**
Regularly review and update fix solutions

### 5. **Implement Rollback**
Have rollback procedures for failed remediations

### 6. **Security Scanning**
Run vulnerability scans regularly (daily/weekly)

### 7. **Certificate Monitoring**
Monitor certificates 30+ days before expiry

### 8. **Resource Limits**
Set appropriate CPU/memory thresholds

---

## 🔗 Additional Resources

- [SOAP API Reference](API_REFERENCE.md)
- [Ansible Playbook Templates](../ansible_playbooks/)
- [Security Best Practices](SECURITY.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

---

**Version:** 2.0.0
**Status:** Production Ready
**License:** MIT
