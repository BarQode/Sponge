"""
Compliance Scanner Module

Implements automated compliance scanning, violation detection, and remediation
for SOC2, ISO27001, and PCI-DSS standards. Supports AWS resource scanning
with auto-remediation capabilities and persistent violation tracking.

Production-ready with comprehensive error handling, logging, and database persistence.
"""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
import hashlib
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


# Setup logging
logger = logging.getLogger(__name__)


class ComplianceStandard(Enum):
    """Supported compliance standards."""
    SOC2 = "SOC2"
    ISO27001 = "ISO27001"
    PCI_DSS = "PCI-DSS"
    HIPAA = "HIPAA"
    GDPR = "GDPR"


class ViolationSeverity(Enum):
    """Violation severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class RemediationStatus(Enum):
    """Status of remediation attempts."""
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"


@dataclass
class CompliancePolicy:
    """Defines a compliance policy with checks and requirements."""

    policy_id: str
    standard: ComplianceStandard
    name: str
    description: str
    checks: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    severity: ViolationSeverity = ViolationSeverity.HIGH

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            'policy_id': self.policy_id,
            'standard': self.standard.value,
            'name': self.name,
            'description': self.description,
            'checks': self.checks,
            'requirements': self.requirements,
            'enabled': self.enabled,
            'severity': self.severity.value
        }


@dataclass
class ComplianceViolation:
    """Represents a detected compliance violation."""

    violation_id: str
    policy_id: str
    resource_id: str
    resource_type: str
    severity: ViolationSeverity
    title: str
    description: str
    remediation_steps: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    remediation_status: RemediationStatus = RemediationStatus.NOT_ATTEMPTED
    remediation_evidence: Optional[str] = None
    auto_remediation_available: bool = False
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            'violation_id': self.violation_id,
            'policy_id': self.policy_id,
            'resource_id': self.resource_id,
            'resource_type': self.resource_type,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'remediation_steps': self.remediation_steps,
            'detected_at': self.detected_at.isoformat(),
            'remediation_status': self.remediation_status.value,
            'remediation_evidence': self.remediation_evidence,
            'auto_remediation_available': self.auto_remediation_available,
            'tags': self.tags
        }


class ComplianceScanner:
    """
    Comprehensive compliance scanner for multiple standards.

    Performs automated scanning of AWS resources and systems for compliance
    violations, with support for auto-remediation and persistent tracking.
    """

    def __init__(self, db_path: str = "/tmp/compliance.db", aws_region: str = "us-east-1"):
        """
        Initialize the compliance scanner.

        Args:
            db_path: Path to SQLite database for violation tracking
            aws_region: AWS region for scanning
        """
        self.db_path = db_path
        self.aws_region = aws_region
        self.violations: List[ComplianceViolation] = []
        self.policies: Dict[str, CompliancePolicy] = {}

        # Initialize AWS clients if available
        self.s3_client = None
        self.iam_client = None
        self.kms_client = None
        self.ec2_client = None

        if HAS_BOTO3:
            try:
                self.s3_client = boto3.client('s3', region_name=aws_region)
                self.iam_client = boto3.client('iam', region_name=aws_region)
                self.kms_client = boto3.client('kms', region_name=aws_region)
                self.ec2_client = boto3.client('ec2', region_name=aws_region)
                logger.info("AWS clients initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS clients: {e}")

        # Initialize database
        self._init_database()

        # Load default policies
        self._load_default_policies()

    def _init_database(self) -> None:
        """Initialize SQLite database for violation tracking."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create violations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS violations (
                    violation_id TEXT PRIMARY KEY,
                    policy_id TEXT,
                    resource_id TEXT,
                    resource_type TEXT,
                    severity TEXT,
                    title TEXT,
                    description TEXT,
                    remediation_steps TEXT,
                    detected_at TEXT,
                    remediation_status TEXT,
                    remediation_evidence TEXT,
                    auto_remediation_available BOOLEAN,
                    tags TEXT,
                    created_at TEXT
                )
            ''')

            # Create compliance history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS compliance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_timestamp TEXT,
                    standard TEXT,
                    violation_count INTEGER,
                    critical_count INTEGER,
                    high_count INTEGER,
                    medium_count INTEGER,
                    low_count INTEGER
                )
            ''')

            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _load_default_policies(self) -> None:
        """Load default compliance policies."""
        self.policies = {
            'SOC2-001': CompliancePolicy(
                policy_id='SOC2-001',
                standard=ComplianceStandard.SOC2,
                name='S3 Public Access Prevention',
                description='Ensure S3 buckets are not publicly accessible',
                checks=['s3_public_access', 's3_bucket_policy'],
                requirements={'public_acl': False, 'public_policy': False},
                severity=ViolationSeverity.CRITICAL
            ),
            'SOC2-002': CompliancePolicy(
                policy_id='SOC2-002',
                standard=ComplianceStandard.SOC2,
                name='Encryption in Transit',
                description='Ensure all data in transit is encrypted',
                checks=['s3_encryption', 'https_enforcement'],
                requirements={'tls_only': True, 'min_tls_version': '1.2'},
                severity=ViolationSeverity.HIGH
            ),
            'ISO27001-001': CompliancePolicy(
                policy_id='ISO27001-001',
                standard=ComplianceStandard.ISO27001,
                name='Access Control',
                description='Enforce multi-factor authentication',
                checks=['mfa_enabled', 'iam_policies'],
                requirements={'mfa_required': True},
                severity=ViolationSeverity.HIGH
            ),
            'ISO27001-002': CompliancePolicy(
                policy_id='ISO27001-002',
                standard=ComplianceStandard.ISO27001,
                name='IAM Policy Restrictions',
                description='Prevent overly permissive IAM policies',
                checks=['iam_permissions', 'wildcard_actions'],
                requirements={'no_wildcard_principal': True, 'no_full_admin': True},
                severity=ViolationSeverity.HIGH
            ),
            'PCI-DSS-001': CompliancePolicy(
                policy_id='PCI-DSS-001',
                standard=ComplianceStandard.PCI_DSS,
                name='Encryption at Rest',
                description='All data at rest must be encrypted',
                checks=['ebs_encryption', 's3_encryption', 'rds_encryption'],
                requirements={'encryption_enabled': True, 'cmk_required': True},
                severity=ViolationSeverity.CRITICAL
            ),
            'PCI-DSS-002': CompliancePolicy(
                policy_id='PCI-DSS-002',
                standard=ComplianceStandard.PCI_DSS,
                name='Network Segmentation',
                description='Enforce security group restrictions',
                checks=['sg_restrictions', 'open_ports'],
                requirements={'no_0_0_0_0_access': True, 'restricted_protocols': True},
                severity=ViolationSeverity.HIGH
            )
        }
        logger.info(f"Loaded {len(self.policies)} default compliance policies")

    def scan_s3_buckets(self) -> List[ComplianceViolation]:
        """
        Scan S3 buckets for public access and encryption issues.

        Returns:
            List of detected violations
        """
        violations = []

        if not self.s3_client:
            logger.warning("S3 client not available")
            return violations

        try:
            response = self.s3_client.list_buckets()
            buckets = response.get('Buckets', [])

            for bucket in buckets:
                bucket_name = bucket['Name']

                # Check public access
                violations.extend(self._check_s3_public_access(bucket_name))

                # Check encryption
                violations.extend(self._check_s3_encryption(bucket_name))

                # Check versioning
                violations.extend(self._check_s3_versioning(bucket_name))

            logger.info(f"Scanned {len(buckets)} S3 buckets, found {len(violations)} violations")
        except ClientError as e:
            logger.error(f"Error scanning S3 buckets: {e}")

        return violations

    def _check_s3_public_access(self, bucket_name: str) -> List[ComplianceViolation]:
        """Check if S3 bucket is publicly accessible."""
        violations = []

        try:
            # Check Public Access Block
            try:
                pab_response = self.s3_client.get_public_access_block(Bucket=bucket_name)
                pab = pab_response['PublicAccessBlockConfiguration']

                if not (pab['BlockPublicAcls'] and pab['BlockPublicPolicy']):
                    violation_id = self._generate_violation_id('S3', bucket_name, 'public_access')
                    violations.append(ComplianceViolation(
                        violation_id=violation_id,
                        policy_id='SOC2-001',
                        resource_id=bucket_name,
                        resource_type='S3Bucket',
                        severity=ViolationSeverity.CRITICAL,
                        title='S3 Bucket Public Access Not Blocked',
                        description=f'S3 bucket {bucket_name} does not have public access blocking enabled',
                        remediation_steps=[
                            'Enable BlockPublicAcls in Public Access Block',
                            'Enable BlockPublicPolicy in Public Access Block',
                            'Enable IgnorePublicAcls in Public Access Block',
                            'Enable RestrictPublicBuckets in Public Access Block'
                        ],
                        auto_remediation_available=True,
                        tags={'resource': bucket_name, 'check_type': 'public_access'}
                    ))
            except ClientError:
                pass

            # Check bucket policy for public statements
            try:
                policy_response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
                policy = json.loads(policy_response['Policy'])

                for statement in policy.get('Statement', []):
                    if statement.get('Principal') == '*' and statement.get('Effect') == 'Allow':
                        violation_id = self._generate_violation_id('S3', bucket_name, 'public_policy')
                        violations.append(ComplianceViolation(
                            violation_id=violation_id,
                            policy_id='SOC2-001',
                            resource_id=bucket_name,
                            resource_type='S3Bucket',
                            severity=ViolationSeverity.CRITICAL,
                            title='S3 Bucket Policy Allows Public Access',
                            description=f'Bucket policy for {bucket_name} contains wildcard principal',
                            remediation_steps=['Remove or restrict wildcard principal in bucket policy'],
                            auto_remediation_available=True,
                            tags={'resource': bucket_name, 'check_type': 'policy'}
                        ))
            except ClientError:
                pass

        except Exception as e:
            logger.error(f"Error checking S3 public access for {bucket_name}: {e}")

        return violations

    def _check_s3_encryption(self, bucket_name: str) -> List[ComplianceViolation]:
        """Check if S3 bucket has encryption enabled."""
        violations = []

        try:
            response = self.s3_client.get_bucket_encryption(Bucket=bucket_name)
            rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])

            if not rules:
                violation_id = self._generate_violation_id('S3', bucket_name, 'encryption')
                violations.append(ComplianceViolation(
                    violation_id=violation_id,
                    policy_id='SOC2-002',
                    resource_id=bucket_name,
                    resource_type='S3Bucket',
                    severity=ViolationSeverity.HIGH,
                    title='S3 Bucket Encryption Not Enabled',
                    description=f'S3 bucket {bucket_name} does not have server-side encryption enabled',
                    remediation_steps=[
                        'Enable server-side encryption (SSE-S3 or SSE-KMS)',
                        'Consider using customer-managed KMS keys for enhanced control'
                    ],
                    auto_remediation_available=True,
                    tags={'resource': bucket_name, 'check_type': 'encryption'}
                ))
        except ClientError as e:
            if e.response['Error']['Code'] != 'ServerSideEncryptionConfigurationNotFoundError':
                logger.error(f"Error checking encryption for {bucket_name}: {e}")
        except Exception as e:
            logger.error(f"Error checking encryption for {bucket_name}: {e}")

        return violations

    def _check_s3_versioning(self, bucket_name: str) -> List[ComplianceViolation]:
        """Check if S3 bucket has versioning enabled."""
        violations = []

        try:
            response = self.s3_client.get_bucket_versioning(Bucket=bucket_name)

            if response.get('Status') != 'Enabled':
                violation_id = self._generate_violation_id('S3', bucket_name, 'versioning')
                violations.append(ComplianceViolation(
                    violation_id=violation_id,
                    policy_id='PCI-DSS-001',
                    resource_id=bucket_name,
                    resource_type='S3Bucket',
                    severity=ViolationSeverity.MEDIUM,
                    title='S3 Bucket Versioning Not Enabled',
                    description=f'S3 bucket {bucket_name} does not have versioning enabled',
                    remediation_steps=['Enable versioning on S3 bucket for data protection'],
                    auto_remediation_available=True,
                    tags={'resource': bucket_name, 'check_type': 'versioning'}
                ))
        except Exception as e:
            logger.error(f"Error checking versioning for {bucket_name}: {e}")

        return violations

    def scan_iam_policies(self) -> List[ComplianceViolation]:
        """
        Scan IAM policies for overly permissive access.

        Returns:
            List of detected violations
        """
        violations = []

        if not self.iam_client:
            logger.warning("IAM client not available")
            return violations

        try:
            # Check for overly permissive policies
            policies = self.iam_client.list_policies(Scope='Local')['Policies']

            for policy in policies:
                violations.extend(self._check_iam_policy_permissions(policy['Arn']))

            # Check user MFA
            users = self.iam_client.list_users()['Users']
            violations.extend(self._check_user_mfa(users))

            logger.info(f"Scanned IAM policies, found {len(violations)} violations")
        except ClientError as e:
            logger.error(f"Error scanning IAM policies: {e}")

        return violations

    def _check_iam_policy_permissions(self, policy_arn: str) -> List[ComplianceViolation]:
        """Check for overly permissive actions in IAM policy."""
        violations = []

        try:
            policy = self.iam_client.get_policy(PolicyArn=policy_arn)['Policy']

            # Get policy version
            version = self.iam_client.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=policy['DefaultVersionId']
            )['PolicyVersion']['Document']

            for statement in version.get('Statement', []):
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]

                # Check for wildcard actions
                if '*' in actions or any('*' in action for action in actions):
                    resource = statement.get('Resource', [])
                    if resource == '*' or resource == ['*']:
                        violation_id = self._generate_violation_id('IAM', policy_arn, 'wildcard')
                        violations.append(ComplianceViolation(
                            violation_id=violation_id,
                            policy_id='ISO27001-002',
                            resource_id=policy_arn,
                            resource_type='IAMPolicy',
                            severity=ViolationSeverity.CRITICAL,
                            title='IAM Policy with Wildcard Permissions',
                            description=f'Policy {policy_arn} allows wildcard actions on all resources',
                            remediation_steps=[
                                'Specify specific actions instead of wildcards',
                                'Limit resource scope to only required resources',
                                'Apply principle of least privilege'
                            ],
                            auto_remediation_available=False,
                            tags={'resource': policy_arn, 'check_type': 'wildcard'}
                        ))
        except Exception as e:
            logger.error(f"Error checking IAM policy {policy_arn}: {e}")

        return violations

    def _check_user_mfa(self, users: List[Dict]) -> List[ComplianceViolation]:
        """Check if IAM users have MFA enabled."""
        violations = []

        try:
            for user in users:
                username = user['UserName']

                # Skip service accounts
                if username.startswith('svc-') or username.startswith('sa-'):
                    continue

                mfa_devices = self.iam_client.list_mfa_devices(UserName=username)['MFADevices']

                if not mfa_devices:
                    violation_id = self._generate_violation_id('IAM', username, 'mfa')
                    violations.append(ComplianceViolation(
                        violation_id=violation_id,
                        policy_id='ISO27001-001',
                        resource_id=username,
                        resource_type='IAMUser',
                        severity=ViolationSeverity.HIGH,
                        title='IAM User Missing MFA',
                        description=f'User {username} does not have MFA enabled',
                        remediation_steps=[
                            'Enable MFA for user',
                            'Use authenticator app or hardware token',
                            'Store backup codes securely'
                        ],
                        auto_remediation_available=False,
                        tags={'resource': username, 'check_type': 'mfa'}
                    ))
        except Exception as e:
            logger.error(f"Error checking user MFA: {e}")

        return violations

    def scan_resource_encryption(self) -> List[ComplianceViolation]:
        """Scan for unencrypted resources (EBS, RDS, etc)."""
        violations = []

        if not self.ec2_client:
            logger.warning("EC2 client not available")
            return violations

        try:
            # Check EBS volumes
            volumes = self.ec2_client.describe_volumes()['Volumes']

            for volume in volumes:
                if not volume.get('Encrypted'):
                    violation_id = self._generate_violation_id('EBS', volume['VolumeId'], 'encryption')
                    violations.append(ComplianceViolation(
                        violation_id=violation_id,
                        policy_id='PCI-DSS-001',
                        resource_id=volume['VolumeId'],
                        resource_type='EBSVolume',
                        severity=ViolationSeverity.HIGH,
                        title='EBS Volume Not Encrypted',
                        description=f'EBS volume {volume["VolumeId"]} is not encrypted',
                        remediation_steps=[
                            'Create encrypted snapshot of volume',
                            'Restore volume from encrypted snapshot',
                            'Terminate unencrypted volume'
                        ],
                        auto_remediation_available=False,
                        tags={'resource': volume['VolumeId'], 'check_type': 'encryption'}
                    ))

            logger.info(f"Scanned {len(volumes)} EBS volumes, found {len(violations)} violations")
        except Exception as e:
            logger.error(f"Error scanning encryption: {e}")

        return violations

    def auto_remediate_violation(self, violation: ComplianceViolation) -> bool:
        """
        Attempt to auto-remediate a violation.

        Args:
            violation: The violation to remediate

        Returns:
            True if remediation succeeded, False otherwise
        """
        if not violation.auto_remediation_available:
            logger.warning(f"Auto-remediation not available for {violation.violation_id}")
            return False

        violation.remediation_status = RemediationStatus.IN_PROGRESS

        try:
            if violation.resource_type == 'S3Bucket':
                if 'public_access' in violation.title.lower():
                    return self._remediate_s3_public_access(violation)
                elif 'encryption' in violation.title.lower():
                    return self._remediate_s3_encryption(violation)
                elif 'versioning' in violation.title.lower():
                    return self._remediate_s3_versioning(violation)

            violation.remediation_status = RemediationStatus.MANUAL_REQUIRED
            return False
        except Exception as e:
            logger.error(f"Error remediating violation {violation.violation_id}: {e}")
            violation.remediation_status = RemediationStatus.FAILED
            return False

    def _remediate_s3_public_access(self, violation: ComplianceViolation) -> bool:
        """Remediate S3 public access violation."""
        try:
            self.s3_client.put_public_access_block(
                Bucket=violation.resource_id,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            violation.remediation_status = RemediationStatus.SUCCESS
            violation.remediation_evidence = f"Public access blocked at {datetime.utcnow().isoformat()}"
            logger.info(f"Successfully remediated {violation.violation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remediate S3 public access: {e}")
            return False

    def _remediate_s3_encryption(self, violation: ComplianceViolation) -> bool:
        """Remediate S3 encryption violation."""
        try:
            self.s3_client.put_bucket_encryption(
                Bucket=violation.resource_id,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            )
            violation.remediation_status = RemediationStatus.SUCCESS
            violation.remediation_evidence = f"Encryption enabled at {datetime.utcnow().isoformat()}"
            logger.info(f"Successfully remediated {violation.violation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remediate S3 encryption: {e}")
            return False

    def _remediate_s3_versioning(self, violation: ComplianceViolation) -> bool:
        """Remediate S3 versioning violation."""
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=violation.resource_id,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            violation.remediation_status = RemediationStatus.SUCCESS
            violation.remediation_evidence = f"Versioning enabled at {datetime.utcnow().isoformat()}"
            logger.info(f"Successfully remediated {violation.violation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remediate S3 versioning: {e}")
            return False

    def save_violation(self, violation: ComplianceViolation) -> bool:
        """
        Save violation to database.

        Args:
            violation: The violation to save

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO violations
                (violation_id, policy_id, resource_id, resource_type, severity,
                 title, description, remediation_steps, detected_at,
                 remediation_status, remediation_evidence, auto_remediation_available, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                violation.violation_id,
                violation.policy_id,
                violation.resource_id,
                violation.resource_type,
                violation.severity.value,
                violation.title,
                violation.description,
                json.dumps(violation.remediation_steps),
                violation.detected_at.isoformat(),
                violation.remediation_status.value,
                violation.remediation_evidence,
                violation.auto_remediation_available,
                json.dumps(violation.tags),
                datetime.utcnow().isoformat()
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to save violation: {e}")
            return False

    def generate_compliance_report(self, standard: Optional[ComplianceStandard] = None) -> Dict[str, Any]:
        """
        Generate compliance report.

        Args:
            standard: Filter report by compliance standard

        Returns:
            Compliance report dictionary
        """
        filtered_violations = self.violations

        if standard:
            filtered_violations = [
                v for v in self.violations
                if self.policies.get(v.policy_id, CompliancePolicy(
                    policy_id='', standard=standard, name='', description=''
                )).standard == standard
            ]

        # Count by severity
        severity_counts = {
            'CRITICAL': len([v for v in filtered_violations if v.severity == ViolationSeverity.CRITICAL]),
            'HIGH': len([v for v in filtered_violations if v.severity == ViolationSeverity.HIGH]),
            'MEDIUM': len([v for v in filtered_violations if v.severity == ViolationSeverity.MEDIUM]),
            'LOW': len([v for v in filtered_violations if v.severity == ViolationSeverity.LOW]),
            'INFO': len([v for v in filtered_violations if v.severity == ViolationSeverity.INFO])
        }

        # Remediation status counts
        remediation_counts = {}
        for status in RemediationStatus:
            remediation_counts[status.value] = len(
                [v for v in filtered_violations if v.remediation_status == status]
            )

        return {
            'report_timestamp': datetime.utcnow().isoformat(),
            'standard': standard.value if standard else 'ALL',
            'total_violations': len(filtered_violations),
            'severity_breakdown': severity_counts,
            'remediation_status': remediation_counts,
            'violations': [v.to_dict() for v in filtered_violations],
            'compliance_score': self._calculate_compliance_score(filtered_violations)
        }

    def _calculate_compliance_score(self, violations: List[ComplianceViolation]) -> float:
        """Calculate compliance score (0-100)."""
        if not violations:
            return 100.0

        # Weight violations by severity
        weights = {
            ViolationSeverity.CRITICAL: 10,
            ViolationSeverity.HIGH: 5,
            ViolationSeverity.MEDIUM: 3,
            ViolationSeverity.LOW: 1,
            ViolationSeverity.INFO: 0.5
        }

        total_weight = sum(
            weights.get(v.severity, 0) for v in violations
        )

        # Score is inversely proportional to weighted violations
        max_weight = 100
        score = max(0, 100 - (total_weight * 100 / max_weight))
        return round(score, 2)

    def _generate_violation_id(self, resource_type: str, resource_id: str, check_type: str) -> str:
        """Generate unique violation ID."""
        content = f"{resource_type}:{resource_id}:{check_type}:{datetime.utcnow().isoformat()}"
        hash_digest = hashlib.sha256(content.encode()).hexdigest()[:8]
        return f"VIO-{resource_type}-{hash_digest}"

    def run_full_scan(self, auto_remediate: bool = False) -> Dict[str, Any]:
        """
        Run full compliance scan across all checks.

        Args:
            auto_remediate: Whether to auto-remediate violations

        Returns:
            Scan results
        """
        logger.info("Starting full compliance scan")
        start_time = datetime.utcnow()

        all_violations = []

        # Run all scans
        all_violations.extend(self.scan_s3_buckets())
        all_violations.extend(self.scan_iam_policies())
        all_violations.extend(self.scan_resource_encryption())

        self.violations = all_violations

        # Auto-remediate if requested
        remediation_results = {}
        if auto_remediate:
            for violation in self.violations:
                if violation.auto_remediation_available:
                    remediation_results[violation.violation_id] = self.auto_remediate_violation(violation)

        # Save all violations to database
        for violation in self.violations:
            self.save_violation(violation)

        # Record scan in history
        self._record_scan_history()

        end_time = datetime.utcnow()

        return {
            'scan_timestamp': start_time.isoformat(),
            'duration_seconds': (end_time - start_time).total_seconds(),
            'total_violations': len(self.violations),
            'auto_remediated': sum(1 for v in remediation_results.values() if v),
            'violations': [v.to_dict() for v in self.violations],
            'compliance_reports': {
                standard.value: self.generate_compliance_report(standard)
                for standard in ComplianceStandard
            }
        }

    def _record_scan_history(self) -> None:
        """Record scan results in history table."""
        try:
            severity_counts = {
                'CRITICAL': len([v for v in self.violations if v.severity == ViolationSeverity.CRITICAL]),
                'HIGH': len([v for v in self.violations if v.severity == ViolationSeverity.HIGH]),
                'MEDIUM': len([v for v in self.violations if v.severity == ViolationSeverity.MEDIUM]),
                'LOW': len([v for v in self.violations if v.severity == ViolationSeverity.LOW])
            }

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO compliance_history
                (scan_timestamp, standard, violation_count, critical_count, high_count, medium_count, low_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.utcnow().isoformat(),
                'ALL',
                len(self.violations),
                severity_counts['CRITICAL'],
                severity_counts['HIGH'],
                severity_counts['MEDIUM'],
                severity_counts['LOW']
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record scan history: {e}")
