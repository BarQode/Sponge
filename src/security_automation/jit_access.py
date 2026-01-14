"""
Just-in-Time (JIT) Access Control with ChatOps

Automates temporary access provisioning with approval workflows
and automatic revocation. Integrates with Slack and other chat platforms.
"""

import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import requests

logger = logging.getLogger(__name__)


@dataclass
class AccessRequest:
    """Access request from a user"""
    request_id: str
    requester: str
    resource: str  # e.g., 'prod-db', 'admin-console'
    permission_level: str  # e.g., 'read', 'write', 'admin'
    duration_minutes: int
    reason: str
    requested_at: datetime
    status: str  # 'pending', 'approved', 'denied', 'expired'
    approver: Optional[str] = None
    approved_at: Optional[datetime] = None


@dataclass
class AccessGrant:
    """Granted access that will be auto-revoked"""
    grant_id: str
    request_id: str
    requester: str
    resource: str
    permission_level: str
    granted_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    auto_revoked: bool = False


class JITAccessManager:
    """
    Just-in-Time Access Control Manager

    Manages temporary access grants with automatic revocation.
    Integrates with IAM systems and chat platforms.
    """

    def __init__(self,
                 db_path: str = "data/jit_access.db",
                 slack_webhook_url: Optional[str] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.slack_webhook_url = slack_webhook_url
        self._init_database()

        # Configure resource access rules
        self.access_rules: Dict[str, Dict[str, Any]] = {}
        self._init_access_rules()

    def _init_database(self):
        """Initialize SQLite database for access tracking"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    requester TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    permission_level TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    approver TEXT NULL,
                    approved_at TIMESTAMP NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_grants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grant_id TEXT UNIQUE NOT NULL,
                    request_id TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    permission_level TEXT NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    revoked_at TIMESTAMP NULL,
                    auto_revoked BOOLEAN DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action TEXT NOT NULL,
                    user TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    details TEXT NOT NULL
                )
            """)

            conn.commit()

    def _init_access_rules(self):
        """Initialize access control rules for resources"""
        self.access_rules = {
            'prod-db': {
                'max_duration_minutes': 60,
                'requires_approval': True,
                'allowed_permissions': ['read', 'write'],
                'approvers': ['security-team', 'db-admins']
            },
            'staging-db': {
                'max_duration_minutes': 240,
                'requires_approval': False,
                'allowed_permissions': ['read', 'write', 'admin'],
                'approvers': []
            },
            'prod-admin': {
                'max_duration_minutes': 30,
                'requires_approval': True,
                'allowed_permissions': ['admin'],
                'approvers': ['security-team', 'management']
            },
            'prod-ssh': {
                'max_duration_minutes': 120,
                'requires_approval': True,
                'allowed_permissions': ['ssh'],
                'approvers': ['sre-team', 'security-team']
            },
            'aws-console': {
                'max_duration_minutes': 480,
                'requires_approval': False,
                'allowed_permissions': ['read', 'write'],
                'approvers': []
            }
        }

    def request_access(self,
                      requester: str,
                      resource: str,
                      permission_level: str,
                      duration_minutes: int,
                      reason: str) -> Optional[AccessRequest]:
        """
        Request temporary access to a resource

        Args:
            requester: Username or email
            resource: Resource identifier
            permission_level: Permission level requested
            duration_minutes: Duration in minutes
            reason: Justification for access

        Returns:
            AccessRequest object or None if invalid
        """
        # Validate resource
        rules = self.access_rules.get(resource)
        if not rules:
            logger.error(f"Unknown resource: {resource}")
            return None

        # Validate permission level
        if permission_level not in rules['allowed_permissions']:
            logger.error(f"Invalid permission level: {permission_level} for {resource}")
            return None

        # Validate duration
        if duration_minutes > rules['max_duration_minutes']:
            logger.error(f"Duration exceeds maximum: {duration_minutes} > {rules['max_duration_minutes']}")
            return None

        # Create request
        request_id = self._generate_request_id(requester, resource)
        requested_at = datetime.now()

        status = 'pending' if rules['requires_approval'] else 'approved'

        request = AccessRequest(
            request_id=request_id,
            requester=requester,
            resource=resource,
            permission_level=permission_level,
            duration_minutes=duration_minutes,
            reason=reason,
            requested_at=requested_at,
            status=status,
            approver=None if rules['requires_approval'] else 'auto-approved'
        )

        # Store request
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO access_requests
                    (request_id, requester, resource, permission_level, duration_minutes,
                     reason, status, approver)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (request.request_id, request.requester, request.resource,
                      request.permission_level, request.duration_minutes,
                      request.reason, request.status, request.approver))
                conn.commit()

            self._audit_log('request_created', requester, resource, {
                'request_id': request_id,
                'permission': permission_level,
                'duration': duration_minutes
            })

            logger.info(f"Access request created: {request_id}")

            # Send notification
            if rules['requires_approval']:
                self._notify_approvers(request, rules['approvers'])
            else:
                # Auto-grant if no approval needed
                self.grant_access(request.request_id, 'auto-approved')

        except Exception as e:
            logger.error(f"Failed to create access request: {e}")
            return None

        return request

    def approve_request(self, request_id: str, approver: str) -> bool:
        """
        Approve an access request

        Args:
            request_id: Request to approve
            approver: Username of approver

        Returns:
            True if approved successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update request status
                conn.execute("""
                    UPDATE access_requests
                    SET status = 'approved', approver = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE request_id = ? AND status = 'pending'
                """, (approver, request_id))
                conn.commit()

                if conn.total_changes == 0:
                    logger.warning(f"Request not found or already processed: {request_id}")
                    return False

            # Grant access
            self.grant_access(request_id, approver)

            self._audit_log('request_approved', approver, request_id, {
                'request_id': request_id
            })

            logger.info(f"Access request approved: {request_id} by {approver}")
            return True

        except Exception as e:
            logger.error(f"Failed to approve request: {e}")
            return False

    def deny_request(self, request_id: str, approver: str, reason: str) -> bool:
        """
        Deny an access request

        Args:
            request_id: Request to deny
            approver: Username of approver
            reason: Reason for denial

        Returns:
            True if denied successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE access_requests
                    SET status = 'denied', approver = ?, approved_at = CURRENT_TIMESTAMP
                    WHERE request_id = ? AND status = 'pending'
                """, (approver, request_id))
                conn.commit()

            self._audit_log('request_denied', approver, request_id, {
                'request_id': request_id,
                'reason': reason
            })

            # Notify requester
            self._notify_denial(request_id, reason)

            logger.info(f"Access request denied: {request_id} by {approver}")
            return True

        except Exception as e:
            logger.error(f"Failed to deny request: {e}")
            return False

    def grant_access(self, request_id: str, approver: str) -> Optional[AccessGrant]:
        """
        Grant access based on an approved request

        Args:
            request_id: Approved request
            approver: Username of approver

        Returns:
            AccessGrant object or None if failed
        """
        try:
            # Get request details
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT requester, resource, permission_level, duration_minutes
                    FROM access_requests
                    WHERE request_id = ? AND status = 'approved'
                """, (request_id,))

                row = cursor.fetchone()
                if not row:
                    logger.error(f"Request not found or not approved: {request_id}")
                    return None

                requester, resource, permission_level, duration_minutes = row

                # Create grant
                grant_id = self._generate_grant_id(request_id)
                granted_at = datetime.now()
                expires_at = granted_at + timedelta(minutes=duration_minutes)

                grant = AccessGrant(
                    grant_id=grant_id,
                    request_id=request_id,
                    requester=requester,
                    resource=resource,
                    permission_level=permission_level,
                    granted_at=granted_at,
                    expires_at=expires_at
                )

                # Store grant
                conn.execute("""
                    INSERT INTO access_grants
                    (grant_id, request_id, requester, resource, permission_level,
                     expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (grant.grant_id, grant.request_id, grant.requester,
                      grant.resource, grant.permission_level, grant.expires_at))
                conn.commit()

            # Actually provision access in IAM system
            self._provision_access(grant)

            self._audit_log('access_granted', approver, resource, {
                'grant_id': grant_id,
                'requester': requester,
                'expires_at': expires_at.isoformat()
            })

            # Notify user
            self._notify_grant(grant)

            logger.info(f"Access granted: {grant_id} for {requester} to {resource}")
            return grant

        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            return None

    def revoke_access(self, grant_id: str, auto_revoke: bool = False) -> bool:
        """
        Revoke access grant

        Args:
            grant_id: Grant to revoke
            auto_revoke: Whether this is automatic revocation

        Returns:
            True if revoked successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get grant details
                cursor = conn.execute("""
                    SELECT requester, resource, permission_level
                    FROM access_grants
                    WHERE grant_id = ? AND revoked_at IS NULL
                """, (grant_id,))

                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Grant not found or already revoked: {grant_id}")
                    return False

                requester, resource, permission_level = row

                # Update grant
                conn.execute("""
                    UPDATE access_grants
                    SET revoked_at = CURRENT_TIMESTAMP, auto_revoked = ?
                    WHERE grant_id = ?
                """, (auto_revoke, grant_id))
                conn.commit()

            # Actually deprovision access in IAM system
            self._deprovision_access(requester, resource, permission_level)

            self._audit_log('access_revoked', 'system' if auto_revoke else requester,
                          resource, {
                              'grant_id': grant_id,
                              'auto_revoked': auto_revoke
                          })

            logger.info(f"Access revoked: {grant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke access: {e}")
            return False

    def revoke_expired_grants(self) -> int:
        """
        Revoke all expired access grants

        Returns:
            Number of grants revoked
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT grant_id
                    FROM access_grants
                    WHERE expires_at < CURRENT_TIMESTAMP AND revoked_at IS NULL
                """)

                expired_grants = [row[0] for row in cursor.fetchall()]

            revoked_count = 0
            for grant_id in expired_grants:
                if self.revoke_access(grant_id, auto_revoke=True):
                    revoked_count += 1

            if revoked_count > 0:
                logger.info(f"Auto-revoked {revoked_count} expired grants")

            return revoked_count

        except Exception as e:
            logger.error(f"Failed to revoke expired grants: {e}")
            return 0

    def _generate_request_id(self, requester: str, resource: str) -> str:
        """Generate unique request ID"""
        timestamp = datetime.now().isoformat()
        data = f"{requester}:{resource}:{timestamp}"
        return f"req_{hashlib.md5(data.encode()).hexdigest()[:12]}"

    def _generate_grant_id(self, request_id: str) -> str:
        """Generate unique grant ID"""
        return f"grant_{hashlib.md5(request_id.encode()).hexdigest()[:12]}"

    def _provision_access(self, grant: AccessGrant):
        """
        Provision access in IAM system

        This is a placeholder - implement actual IAM integration
        (AWS IAM, Azure AD, LDAP, etc.)
        """
        logger.info(f"[IAM] Provisioning {grant.permission_level} access for "
                   f"{grant.requester} to {grant.resource}")

        # Example AWS IAM integration:
        # import boto3
        # iam = boto3.client('iam')
        # iam.attach_user_policy(
        #     UserName=grant.requester,
        #     PolicyArn=f"arn:aws:iam::policy/{grant.resource}-{grant.permission_level}"
        # )

    def _deprovision_access(self, user: str, resource: str, permission: str):
        """
        Deprovision access from IAM system

        This is a placeholder - implement actual IAM integration
        """
        logger.info(f"[IAM] Deprovisioning {permission} access for {user} to {resource}")

        # Example AWS IAM integration:
        # iam.detach_user_policy(
        #     UserName=user,
        #     PolicyArn=f"arn:aws:iam::policy/{resource}-{permission}"
        # )

    def _notify_approvers(self, request: AccessRequest, approvers: List[str]):
        """Send notification to approvers via Slack"""
        if not self.slack_webhook_url:
            logger.warning("Slack webhook not configured, skipping notification")
            return

        message = {
            "text": f"🔐 Access Request Pending Approval",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔐 Access Request Pending Approval"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Requester:*\n{request.requester}"},
                        {"type": "mrkdwn", "text": f"*Resource:*\n{request.resource}"},
                        {"type": "mrkdwn", "text": f"*Permission:*\n{request.permission_level}"},
                        {"type": "mrkdwn", "text": f"*Duration:*\n{request.duration_minutes} minutes"},
                        {"type": "mrkdwn", "text": f"*Reason:*\n{request.reason}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Approvers: {', '.join([f'@{a}' for a in approvers])}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve"},
                            "style": "primary",
                            "value": request.request_id,
                            "action_id": "approve_access"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Deny"},
                            "style": "danger",
                            "value": request.request_id,
                            "action_id": "deny_access"
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(self.slack_webhook_url, json=message, timeout=10)
            if response.status_code == 200:
                logger.info("Approval notification sent to Slack")
            else:
                logger.error(f"Failed to send Slack notification: {response.text}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    def _notify_grant(self, grant: AccessGrant):
        """Notify user of granted access"""
        if not self.slack_webhook_url:
            return

        message = {
            "text": f"✅ Access Granted to {grant.requester}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Access Granted*\n\n"
                               f"User: {grant.requester}\n"
                               f"Resource: {grant.resource}\n"
                               f"Permission: {grant.permission_level}\n"
                               f"Expires: {grant.expires_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                               f"Grant ID: `{grant.grant_id}`"
                    }
                }
            ]
        }

        try:
            requests.post(self.slack_webhook_url, json=message, timeout=10)
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    def _notify_denial(self, request_id: str, reason: str):
        """Notify user of denied request"""
        # Implement notification logic
        logger.info(f"Access request denied: {request_id} - {reason}")

    def _audit_log(self, action: str, user: str, resource: str, details: Dict[str, Any]):
        """Log access action to audit trail"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO access_audit_log (action, user, resource, details)
                    VALUES (?, ?, ?, ?)
                """, (action, user, resource, json.dumps(details)))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_active_grants(self, resource: Optional[str] = None) -> List[AccessGrant]:
        """Get all active (non-expired, non-revoked) grants"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if resource:
                    cursor = conn.execute("""
                        SELECT grant_id, request_id, requester, resource, permission_level,
                               granted_at, expires_at, revoked_at, auto_revoked
                        FROM access_grants
                        WHERE resource = ? AND revoked_at IS NULL
                        AND expires_at > CURRENT_TIMESTAMP
                        ORDER BY expires_at
                    """, (resource,))
                else:
                    cursor = conn.execute("""
                        SELECT grant_id, request_id, requester, resource, permission_level,
                               granted_at, expires_at, revoked_at, auto_revoked
                        FROM access_grants
                        WHERE revoked_at IS NULL
                        AND expires_at > CURRENT_TIMESTAMP
                        ORDER BY expires_at
                    """)

                grants = []
                for row in cursor.fetchall():
                    grant = AccessGrant(
                        grant_id=row[0],
                        request_id=row[1],
                        requester=row[2],
                        resource=row[3],
                        permission_level=row[4],
                        granted_at=datetime.fromisoformat(row[5]),
                        expires_at=datetime.fromisoformat(row[6]),
                        revoked_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        auto_revoked=bool(row[8])
                    )
                    grants.append(grant)

                return grants

        except Exception as e:
            logger.error(f"Failed to get active grants: {e}")
            return []
