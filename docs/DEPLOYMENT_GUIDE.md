# Sponge - Complete Deployment Guide

## IMPORTANT NOTE

**Sponge is 100% FREE and OPEN-SOURCE software.**

This deployment guide is for **optional advanced deployment scenarios** using AWS EKS. You can use Sponge completely free by running it locally with:

```bash
pip install -r requirements.txt
python main.py
```

The following guide is only needed if you want to deploy Sponge on production cloud infrastructure.

---

## Prerequisites

1. **AWS Account** with administrator access
2. **Tools Installed:**
   - Terraform >= 1.0
   - kubectl >= 1.28
   - AWS CLI >= 2.0
   - Docker >= 20.10
   - helm >= 3.0

3. **Domain:** 5ponge.com registered in Route 53

---

## Phase 1: Infrastructure Deployment (Terraform)

### Step 1: Initialize Terraform Backend

```bash
cd terraform

# Create S3 bucket for state
aws s3api create-bucket \
  --bucket sponge-terraform-state \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket sponge-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region us-east-1
```

### Step 2: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review plan
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan
```

**Expected Duration:** 20-30 minutes

**Resources Created:**
- VPC with public/private subnets across 3 AZs
- NAT Gateways
- EKS Cluster (1.28)
- Node Groups (backend, ML workers)
- RDS PostgreSQL (Multi-AZ)
- ElastiCache Redis
- ECR Repositories
- IAM Roles and Policies
- Secrets Manager secrets

### Step 3: Configure kubectl

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name sponge-prod

# Verify connection
kubectl get nodes
```

---

## Phase 2: Build and Push Container Images

### Step 1: Authenticate to ECR

```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### Step 2: Build Images

```bash
# Backend
cd backend
docker build -t sponge-backend:v1.0.0 .
docker tag sponge-backend:v1.0.0 \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sponge-backend:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sponge-backend:latest

# Frontend
cd ../frontend
docker build -t sponge-frontend:v1.0.0 .
docker tag sponge-frontend:v1.0.0 \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sponge-frontend:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sponge-frontend:latest

# ML Worker
cd ../backend/models
docker build -t sponge-ml-worker:v1.0.0 .
docker tag sponge-ml-worker:v1.0.0 \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sponge-ml-worker:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/sponge-ml-worker:latest
```

---

## Phase 3: Deploy Applications to EKS

### Step 1: Create Namespace and Secrets

```bash
cd kubernetes

# Create namespace
kubectl apply -f 00-namespace.yaml

# Update secrets with actual values
# Edit 02-secrets.yaml with real credentials
kubectl apply -f 02-secrets.yaml
```

### Step 2: Deploy ConfigMap

```bash
kubectl apply -f 01-configmap.yaml
```

### Step 3: Deploy Backend

```bash
# Update image URL in deployment
sed -i 's/ACCOUNT_ID/YOUR_ACCOUNT_ID/g' 03-backend-deployment.yaml

kubectl apply -f 03-backend-deployment.yaml

# Wait for pods
kubectl wait --for=condition=ready pod \
  -l app=sponge,component=backend \
  -n sponge-prod \
  --timeout=300s
```

### Step 4: Deploy ML Workers

```bash
sed -i 's/ACCOUNT_ID/YOUR_ACCOUNT_ID/g' 04-ml-worker-deployment.yaml
kubectl apply -f 04-ml-worker-deployment.yaml
```

### Step 5: Deploy Ingress

```bash
# Update certificate ARN
sed -i 's/CERT_ID/YOUR_CERT_ID/g' 05-ingress.yaml
kubectl apply -f 05-ingress.yaml

# Get ALB DNS
kubectl get ingress -n sponge-prod
```

---

## Phase 4: DNS Configuration

### Step 1: Create Route 53 Records

```bash
# Get ALB DNS from ingress
ALB_DNS=$(kubectl get ingress sponge-ingress -n sponge-prod \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Create A record (alias to ALB)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.5ponge.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "'$ALB_DNS'",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'
```

---

## Phase 5: Database Setup

### Step 1: Connect to RDS

```bash
# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Get password from Secrets Manager
DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id sponge-prod/postgres-password \
  --query SecretString \
  --output text)

# Connect
psql -h $RDS_ENDPOINT -U spongeadmin -d sponge
```

### Step 2: Run Migrations

```bash
# From backend directory
cd backend
python -m alembic upgrade head
```

---

## Phase 6: Verification

### Step 1: Health Checks

```bash
# Backend health
curl https://api.5ponge.com/health

# Check pods
kubectl get pods -n sponge-prod

# Check logs
kubectl logs -f deployment/sponge-backend -n sponge-prod
```

### Step 2: Test API

```bash
# Test authentication endpoint
curl -X POST https://api.5ponge.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass"
  }'
```

---

## Phase 7: Monitoring Setup

### Step 1: CloudWatch Container Insights

```bash
# Install CloudWatch agent
kubectl apply -f \
  https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
```

### Step 2: Configure Alarms

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name sponge-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EKS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## Troubleshooting

### Common Issues

**1. Pods stuck in Pending**
```bash
# Check events
kubectl describe pod POD_NAME -n sponge-prod

# Check node resources
kubectl top nodes
```

**2. Cannot pull image from ECR**
```bash
# Check IAM role
kubectl describe sa sponge-sa -n sponge-prod

# Verify ECR permissions
aws ecr describe-repositories
```

**3. Database connection issues**
```bash
# Check security groups
aws ec2 describe-security-groups \
  --filters Name=tag:Name,Values=sponge-prod-rds-sg

# Test connectivity from pod
kubectl run -it --rm debug --image=postgres:15 \
  --restart=Never -n sponge-prod -- \
  psql -h RDS_ENDPOINT -U spongeadmin -d sponge
```

---

## Scaling Guide

### Horizontal Pod Autoscaling

```bash
# Backend scaling
kubectl autoscale deployment sponge-backend \
  -n sponge-prod \
  --cpu-percent=70 \
  --min=3 \
  --max=10
```

### Cluster Autoscaling

```bash
# Update node group desired capacity
aws eks update-nodegroup-config \
  --cluster-name sponge-prod \
  --nodegroup-name backend \
  --scaling-config desiredSize=5,minSize=3,maxSize=15
```

---

## Backup and Disaster Recovery

### Database Backups

```bash
# Manual snapshot
aws rds create-db-snapshot \
  --db-instance-identifier sponge-prod \
  --db-snapshot-identifier sponge-prod-manual-$(date +%Y%m%d)
```

### State Backup

```bash
# Backup Terraform state
aws s3 cp s3://sponge-terraform-state/prod/terraform.tfstate \
  ./backups/terraform.tfstate.$(date +%Y%m%d)
```

---

## Security Checklist

- [ ] Enable MFA for AWS root account
- [ ] Rotate database passwords monthly
- [ ] Enable AWS GuardDuty
- [ ] Configure AWS WAF rules
- [ ] Enable VPC Flow Logs
- [ ] Review IAM policies quarterly
- [ ] Enable encryption at rest for EBS volumes
- [ ] Configure SSL/TLS certificates
- [ ] Enable audit logging
- [ ] Set up AWS Config rules

---

## Cost Optimization

**Immediate:**
1. Use Spot Instances for ML workers
2. Enable S3 Intelligent Tiering
3. Delete old ECR images (lifecycle policy)
4. Use Reserved Instances for steady workloads

**Ongoing:**
5. Monitor CloudWatch costs
6. Right-size RDS instances based on metrics
7. Use Auto Scaling to scale down during off-hours
8. Review NAT Gateway usage (consider NAT instances)

---

## Next Steps

1. Set up CI/CD pipeline (GitLab)
2. Configure monitoring dashboards
3. Implement logging aggregation
4. Set up alerts and notifications
5. Create runbooks for common issues
6. Schedule regular security audits
7. Plan for multi-region deployment

---

## Support

For issues or questions:
- Documentation: https://docs.5ponge.com
- Support: support@5ponge.com
- Status Page: https://status.5ponge.com
