terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  backend "s3" {
    bucket         = "sponge-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Sponge"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Local variables
locals {
  cluster_name = "sponge-${var.environment}"

  # ECR repositories needed
  ecr_repositories = [
    "sponge-backend",
    "sponge-frontend",
    "sponge-ml-worker"
  ]

  # Convert list to map for for_each
  ecr_repo_map = { for repo in local.ecr_repositories : repo => repo }

  common_tags = {
    Project     = "Sponge"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  environment        = var.environment
  vpc_cidr          = var.vpc_cidr
  availability_zones = var.availability_zones

  tags = local.common_tags
}

# EKS Cluster Module
module "eks" {
  source = "./modules/eks"

  cluster_name       = local.cluster_name
  cluster_version    = var.kubernetes_version
  vpc_id            = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  node_groups = {
    backend = {
      desired_size   = 3
      min_size      = 2
      max_size      = 10
      instance_types = ["t3.large"]
      capacity_type  = "ON_DEMAND"
      labels = {
        workload-type = "backend"
      }
    }

    ml_workers = {
      desired_size   = 2
      min_size      = 1
      max_size      = 5
      instance_types = ["c5.2xlarge"]
      capacity_type  = "SPOT"
      labels = {
        workload-type = "ml"
      }
      taints = [{
        key    = "ml-workload"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  tags = local.common_tags

  depends_on = [module.vpc]
}

# RDS PostgreSQL Module
module "rds" {
  source = "./modules/rds"

  identifier          = "sponge-${var.environment}"
  engine_version      = "15.3"
  instance_class      = "db.t3.medium"
  allocated_storage   = 100
  database_name       = "sponge"
  master_username     = "spongeadmin"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  multi_az           = true
  backup_retention   = 7

  tags = local.common_tags

  depends_on = [module.vpc]
}

# ElastiCache Redis Module
module "redis" {
  source = "./modules/redis"

  cluster_id         = "sponge-${var.environment}"
  node_type          = "cache.t3.medium"
  num_cache_nodes    = 2
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.private_subnet_ids

  tags = local.common_tags

  depends_on = [module.vpc]
}

# ECR Repositories
resource "aws_ecr_repository" "repos" {
  for_each = local.ecr_repo_map

  name                 = each.value
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = local.common_tags
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "repo_policy" {
  for_each = aws_ecr_repository.repos

  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# IAM Policy for ECR Access
data "aws_iam_policy_document" "ecr_policy" {
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload"
    ]
    resources = [for repo in aws_ecr_repository.repos : repo.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ecr_policy" {
  name        = "sponge-ecr-access-${var.environment}"
  description = "Policy for ECR access"
  policy      = data.aws_iam_policy_document.ecr_policy.json
}

# IAM Group for CI/CD
resource "aws_iam_group" "cicd" {
  name = "sponge-cicd-${var.environment}"
}

resource "aws_iam_group_policy_attachment" "cicd_ecr" {
  group      = aws_iam_group.cicd.name
  policy_arn = aws_iam_policy.ecr_policy.arn
}

# Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name        = "sponge-${var.environment}/postgres-password"
  description = "PostgreSQL master password"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# OIDC Provider for EKS
data "tls_certificate" "eks" {
  url = module.eks.cluster_oidc_issuer_url
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = module.eks.cluster_oidc_issuer_url

  tags = local.common_tags
}

# IAM Role for Service Account (IRSA)
module "irsa_secrets_manager" {
  source = "./modules/irsa"

  cluster_name              = local.cluster_name
  oidc_provider_arn        = aws_iam_openid_connect_provider.eks.arn
  oidc_provider_url        = module.eks.cluster_oidc_issuer_url
  service_account_name     = "sponge-sa"
  service_account_namespace = "sponge-prod"

  policy_arns = [
    "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
    "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  ]

  tags = local.common_tags

  depends_on = [module.eks, aws_iam_openid_connect_provider.eks]
}

# Install AWS Load Balancer Controller
module "aws_load_balancer_controller" {
  source = "./modules/helm-charts"

  cluster_name          = local.cluster_name
  cluster_endpoint      = module.eks.cluster_endpoint
  cluster_ca_certificate = module.eks.cluster_certificate_authority_data
  oidc_provider_arn     = aws_iam_openid_connect_provider.eks.arn

  depends_on = [module.eks]
}

# Install CSI Driver for Secrets
module "secrets_store_csi_driver" {
  source = "./modules/csi-driver"

  cluster_name          = local.cluster_name
  cluster_endpoint      = module.eks.cluster_endpoint
  cluster_ca_certificate = module.eks.cluster_certificate_authority_data

  depends_on = [module.eks]
}
