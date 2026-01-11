"""
Certificate Manager

Auto-renews SSL/TLS certificates and manages security policies.
"""

import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class CertificateManager:
    """Manages SSL/TLS certificates and security policies"""

    def __init__(self):
        """Initialize certificate manager"""
        self.cert_dir = Path('/etc/sponge/certs')
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.policy_dir = Path('/etc/sponge/policies')
        self.policy_dir.mkdir(parents=True, exist_ok=True)

    def renew_certificate(self, domain: str, cert_type: str = 'ssl') -> Dict[str, Any]:
        """
        Renew certificate for domain

        Args:
            domain: Domain name
            cert_type: Certificate type (ssl, tls, etc.)

        Returns:
            Renewal result
        """
        logger.info(f"Renewing {cert_type} certificate for {domain}")

        result = {
            'domain': domain,
            'cert_type': cert_type,
            'status': 'pending',
            'message': '',
            'cert_path': '',
            'timestamp': datetime.now().isoformat()
        }

        try:
            # Use certbot for Let's Encrypt certificates
            if self._use_certbot(domain):
                result.update(self._renew_with_certbot(domain))
            # Use custom CA
            else:
                result.update(self._renew_with_custom_ca(domain))

            # Update security policies if needed
            if result['status'] == 'success':
                self._update_security_policies(domain)

            return result

        except Exception as e:
            logger.error(f"Certificate renewal failed: {e}")
            result['status'] = 'failed'
            result['message'] = str(e)
            return result

    def _use_certbot(self, domain: str) -> bool:
        """Check if certbot should be used"""
        # Use certbot for public domains
        return not domain.startswith('internal.')

    def _renew_with_certbot(self, domain: str) -> Dict[str, Any]:
        """Renew certificate using certbot"""
        logger.info(f"Using certbot for {domain}")

        try:
            # Run certbot renew
            cmd = [
                'certbot', 'renew',
                '--domain', domain,
                '--non-interactive',
                '--agree-tos',
                '--quiet'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
                return {
                    'status': 'success',
                    'message': 'Certificate renewed successfully',
                    'cert_path': cert_path
                }
            else:
                return {
                    'status': 'failed',
                    'message': f"Certbot failed: {result.stderr}"
                }

        except FileNotFoundError:
            logger.warning("Certbot not installed")
            return {
                'status': 'failed',
                'message': 'Certbot not installed'
            }
        except subprocess.TimeoutExpired:
            return {
                'status': 'failed',
                'message': 'Certbot renewal timed out'
            }

    def _renew_with_custom_ca(self, domain: str) -> Dict[str, Any]:
        """Renew certificate using custom CA"""
        logger.info(f"Using custom CA for {domain}")

        try:
            # Generate new certificate
            cert_path = self.cert_dir / f"{domain}.crt"
            key_path = self.cert_dir / f"{domain}.key"

            # Generate private key
            subprocess.run(
                ['openssl', 'genrsa', '-out', str(key_path), '2048'],
                check=True,
                capture_output=True
            )

            # Generate CSR
            csr_path = self.cert_dir / f"{domain}.csr"
            subprocess.run(
                [
                    'openssl', 'req', '-new',
                    '-key', str(key_path),
                    '-out', str(csr_path),
                    '-subj', f'/CN={domain}'
                ],
                check=True,
                capture_output=True
            )

            # Sign certificate (simplified - use proper CA in production)
            subprocess.run(
                [
                    'openssl', 'x509', '-req',
                    '-in', str(csr_path),
                    '-signkey', str(key_path),
                    '-out', str(cert_path),
                    '-days', '365'
                ],
                check=True,
                capture_output=True
            )

            return {
                'status': 'success',
                'message': 'Certificate generated successfully',
                'cert_path': str(cert_path)
            }

        except subprocess.CalledProcessError as e:
            return {
                'status': 'failed',
                'message': f"Certificate generation failed: {e}"
            }

    def _update_security_policies(self, domain: str):
        """Update security policies for domain"""
        logger.info(f"Updating security policies for {domain}")

        # Update SSL/TLS policy
        policy = {
            'domain': domain,
            'min_tls_version': '1.2',
            'ciphers': [
                'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384',
                'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256'
            ],
            'hsts_enabled': True,
            'hsts_max_age': 31536000,
            'updated_at': datetime.now().isoformat()
        }

        policy_path = self.policy_dir / f"{domain}_tls_policy.json"
        with open(policy_path, 'w') as f:
            json.dump(policy, f, indent=2)

        logger.info(f"Policy updated: {policy_path}")

    def check_certificate_expiry(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Check certificate expiration

        Args:
            domain: Domain to check

        Returns:
            Certificate info or None
        """
        try:
            import ssl
            import socket

            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_remaining = (not_after - datetime.now()).days

                    return {
                        'domain': domain,
                        'expires_at': not_after.isoformat(),
                        'days_remaining': days_remaining,
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'subject': dict(x[0] for x in cert['subject'])
                    }

        except Exception as e:
            logger.error(f"Failed to check certificate for {domain}: {e}")
            return None

    def auto_renew_expiring_certificates(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        """
        Automatically renew certificates expiring soon

        Args:
            days_threshold: Renew if expiring within this many days

        Returns:
            List of renewal results
        """
        logger.info(f"Checking for certificates expiring within {days_threshold} days")

        results = []
        domains = self._get_monitored_domains()

        for domain in domains:
            cert_info = self.check_certificate_expiry(domain)

            if cert_info and cert_info['days_remaining'] < days_threshold:
                logger.info(f"Certificate for {domain} expires in {cert_info['days_remaining']} days")

                renewal_result = self.renew_certificate(domain)
                results.append(renewal_result)

        return results

    def _get_monitored_domains(self) -> List[str]:
        """Get list of monitored domains"""
        # In production, load from configuration
        config_file = self.policy_dir / 'monitored_domains.json'

        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
                return config.get('domains', [])

        return []

    def update_security_policy(self, policy_name: str, policy_config: Dict[str, Any]) -> bool:
        """
        Update security policy

        Args:
            policy_name: Policy name
            policy_config: Policy configuration

        Returns:
            True if successful
        """
        logger.info(f"Updating policy: {policy_name}")

        try:
            policy_path = self.policy_dir / f"{policy_name}.json"

            policy_config['updated_at'] = datetime.now().isoformat()

            with open(policy_path, 'w') as f:
                json.dump(policy_config, f, indent=2)

            # Apply policy
            self._apply_policy(policy_name, policy_config)

            return True

        except Exception as e:
            logger.error(f"Failed to update policy: {e}")
            return False

    def _apply_policy(self, policy_name: str, policy_config: Dict[str, Any]):
        """Apply security policy to systems"""
        logger.info(f"Applying policy: {policy_name}")

        # In production, integrate with:
        # - AWS Security Groups
        # - Kubernetes Network Policies
        # - Firewall rules
        # - WAF configurations

        # Example: Update nginx SSL configuration
        if 'tls_version' in policy_config:
            logger.info(f"TLS version policy: {policy_config['tls_version']}")

        if 'ciphers' in policy_config:
            logger.info(f"Cipher policy: {policy_config['ciphers']}")
