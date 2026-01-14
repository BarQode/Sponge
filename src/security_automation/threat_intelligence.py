"""
Threat Intelligence Integration

Integrates with threat intelligence feeds and reputation services
to enrich security incidents with threat data.
"""

import logging
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class ThreatIndicator:
    """Threat indicator (IOC)"""
    indicator_type: str  # 'ip', 'domain', 'hash', 'email', 'url'
    value: str
    threat_type: str  # 'malware', 'phishing', 'c2', 'scanner', 'spam'
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence: int  # 0-100
    first_seen: datetime
    last_seen: datetime
    sources: List[str]
    metadata: Dict[str, Any]


@dataclass
class IPReputation:
    """IP reputation data"""
    ip: str
    reputation_score: int  # 0-100, lower is worse
    is_malicious: bool
    abuse_confidence: int  # 0-100
    country: str
    asn: str
    usage_type: str  # 'datacenter', 'residential', 'mobile', etc.
    reports: int
    last_reported: Optional[datetime]
    categories: List[str]


class ThreatIntelligence:
    """
    Threat Intelligence Integration

    Aggregates threat data from multiple sources and provides
    reputation lookups for security investigations.
    """

    def __init__(self,
                 db_path: str = "data/threat_intelligence.db",
                 abuseipdb_api_key: Optional[str] = None,
                 virustotal_api_key: Optional[str] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.abuseipdb_api_key = abuseipdb_api_key
        self.virustotal_api_key = virustotal_api_key
        self._init_database()

    def _init_database(self):
        """Initialize threat intelligence database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS threat_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    threat_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence INTEGER NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sources TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    UNIQUE(indicator_type, value)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS ip_reputation_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT UNIQUE NOT NULL,
                    reputation_score INTEGER NOT NULL,
                    is_malicious BOOLEAN NOT NULL,
                    abuse_confidence INTEGER NOT NULL,
                    country TEXT,
                    asn TEXT,
                    usage_type TEXT,
                    reports INTEGER NOT NULL,
                    last_reported TIMESTAMP,
                    categories TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS threat_feeds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feed_name TEXT UNIQUE NOT NULL,
                    feed_url TEXT NOT NULL,
                    feed_type TEXT NOT NULL,
                    last_updated TIMESTAMP,
                    indicator_count INTEGER DEFAULT 0,
                    enabled BOOLEAN DEFAULT 1
                )
            """)

            conn.commit()

    def check_ip_reputation(self, ip: str, use_cache: bool = True) -> Optional[IPReputation]:
        """
        Check IP reputation

        Args:
            ip: IP address to check
            use_cache: Whether to use cached results (24h TTL)

        Returns:
            IPReputation object or None
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached_ip_reputation(ip)
            if cached:
                logger.info(f"Using cached reputation for IP: {ip}")
                return cached

        # Check AbuseIPDB if API key available
        if self.abuseipdb_api_key:
            reputation = self._check_abuseipdb(ip)
            if reputation:
                self._cache_ip_reputation(reputation)
                return reputation

        # Fallback to local threat feed
        return self._check_local_threat_feed(ip)

    def _check_abuseipdb(self, ip: str) -> Optional[IPReputation]:
        """Check IP against AbuseIPDB"""
        try:
            headers = {
                'Key': self.abuseipdb_api_key,
                'Accept': 'application/json'
            }

            response = requests.get(
                'https://api.abuseipdb.com/api/v2/check',
                headers=headers,
                params={'ipAddress': ip, 'maxAgeInDays': 90},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json().get('data', {})

                reputation = IPReputation(
                    ip=ip,
                    reputation_score=100 - data.get('abuseConfidenceScore', 0),
                    is_malicious=data.get('abuseConfidenceScore', 0) > 50,
                    abuse_confidence=data.get('abuseConfidenceScore', 0),
                    country=data.get('countryCode', 'Unknown'),
                    asn=data.get('isp', 'Unknown'),
                    usage_type=data.get('usageType', 'Unknown'),
                    reports=data.get('totalReports', 0),
                    last_reported=datetime.fromisoformat(data['lastReportedAt']) if data.get('lastReportedAt') else None,
                    categories=[cat for cat in data.get('reports', [])]
                )

                logger.info(f"AbuseIPDB reputation for {ip}: score={reputation.reputation_score}")
                return reputation

            else:
                logger.error(f"AbuseIPDB API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error checking AbuseIPDB: {e}")
            return None

    def check_file_hash(self, file_hash: str, hash_type: str = 'sha256') -> Optional[Dict[str, Any]]:
        """
        Check file hash against VirusTotal

        Args:
            file_hash: File hash to check
            hash_type: Hash type (md5, sha1, sha256)

        Returns:
            Dictionary with scan results or None
        """
        if not self.virustotal_api_key:
            logger.warning("VirusTotal API key not configured")
            return None

        try:
            headers = {'x-apikey': self.virustotal_api_key}

            response = requests.get(
                f'https://www.virustotal.com/api/v3/files/{file_hash}',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json().get('data', {})
                attributes = data.get('attributes', {})
                stats = attributes.get('last_analysis_stats', {})

                result = {
                    'hash': file_hash,
                    'hash_type': hash_type,
                    'malicious': stats.get('malicious', 0),
                    'suspicious': stats.get('suspicious', 0),
                    'undetected': stats.get('undetected', 0),
                    'harmless': stats.get('harmless', 0),
                    'is_malicious': stats.get('malicious', 0) > 0,
                    'detection_rate': f"{stats.get('malicious', 0)}/{sum(stats.values())}",
                    'last_analysis': attributes.get('last_analysis_date', 0)
                }

                logger.info(f"VirusTotal scan for {file_hash}: {result['detection_rate']} detections")
                return result

            else:
                logger.error(f"VirusTotal API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error checking VirusTotal: {e}")
            return None

    def check_domain_reputation(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Check domain reputation

        Args:
            domain: Domain to check

        Returns:
            Dictionary with reputation data or None
        """
        if not self.virustotal_api_key:
            return self._check_local_threat_feed(domain, indicator_type='domain')

        try:
            headers = {'x-apikey': self.virustotal_api_key}

            response = requests.get(
                f'https://www.virustotal.com/api/v3/domains/{domain}',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json().get('data', {})
                attributes = data.get('attributes', {})
                stats = attributes.get('last_analysis_stats', {})

                result = {
                    'domain': domain,
                    'malicious': stats.get('malicious', 0),
                    'suspicious': stats.get('suspicious', 0),
                    'is_malicious': stats.get('malicious', 0) > 3,  # Threshold
                    'categories': attributes.get('categories', {}),
                    'reputation': attributes.get('reputation', 0)
                }

                return result

            else:
                logger.error(f"VirusTotal API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error checking domain: {e}")
            return None

    def add_threat_indicator(self,
                            indicator_type: str,
                            value: str,
                            threat_type: str,
                            severity: str,
                            confidence: int,
                            source: str,
                            metadata: Dict[str, Any] = None) -> bool:
        """
        Add threat indicator to database

        Args:
            indicator_type: Type of indicator
            value: Indicator value
            threat_type: Type of threat
            severity: Severity level
            confidence: Confidence score (0-100)
            source: Source of intelligence
            metadata: Additional metadata

        Returns:
            True if added successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if indicator exists
                cursor = conn.execute("""
                    SELECT sources, metadata FROM threat_indicators
                    WHERE indicator_type = ? AND value = ?
                """, (indicator_type, value))

                existing = cursor.fetchone()

                if existing:
                    # Update existing indicator
                    existing_sources = json.loads(existing[0])
                    if source not in existing_sources:
                        existing_sources.append(source)

                    existing_metadata = json.loads(existing[1])
                    if metadata:
                        existing_metadata.update(metadata)

                    conn.execute("""
                        UPDATE threat_indicators
                        SET sources = ?, metadata = ?, last_seen = CURRENT_TIMESTAMP,
                            threat_type = ?, severity = ?, confidence = ?
                        WHERE indicator_type = ? AND value = ?
                    """, (json.dumps(existing_sources), json.dumps(existing_metadata),
                          threat_type, severity, confidence, indicator_type, value))

                else:
                    # Insert new indicator
                    conn.execute("""
                        INSERT INTO threat_indicators
                        (indicator_type, value, threat_type, severity, confidence,
                         sources, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (indicator_type, value, threat_type, severity, confidence,
                          json.dumps([source]), json.dumps(metadata or {})))

                conn.commit()

            logger.info(f"Added threat indicator: {indicator_type}={value}")
            return True

        except Exception as e:
            logger.error(f"Failed to add threat indicator: {e}")
            return False

    def get_threat_indicator(self, indicator_type: str, value: str) -> Optional[ThreatIndicator]:
        """Get threat indicator from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT indicator_type, value, threat_type, severity, confidence,
                           first_seen, last_seen, sources, metadata
                    FROM threat_indicators
                    WHERE indicator_type = ? AND value = ?
                """, (indicator_type, value))

                row = cursor.fetchone()
                if not row:
                    return None

                return ThreatIndicator(
                    indicator_type=row[0],
                    value=row[1],
                    threat_type=row[2],
                    severity=row[3],
                    confidence=row[4],
                    first_seen=datetime.fromisoformat(row[5]),
                    last_seen=datetime.fromisoformat(row[6]),
                    sources=json.loads(row[7]),
                    metadata=json.loads(row[8])
                )

        except Exception as e:
            logger.error(f"Failed to get threat indicator: {e}")
            return None

    def _get_cached_ip_reputation(self, ip: str) -> Optional[IPReputation]:
        """Get cached IP reputation if not expired"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT ip, reputation_score, is_malicious, abuse_confidence,
                           country, asn, usage_type, reports, last_reported, categories
                    FROM ip_reputation_cache
                    WHERE ip = ? AND expires_at > CURRENT_TIMESTAMP
                """, (ip,))

                row = cursor.fetchone()
                if not row:
                    return None

                return IPReputation(
                    ip=row[0],
                    reputation_score=row[1],
                    is_malicious=bool(row[2]),
                    abuse_confidence=row[3],
                    country=row[4],
                    asn=row[5],
                    usage_type=row[6],
                    reports=row[7],
                    last_reported=datetime.fromisoformat(row[8]) if row[8] else None,
                    categories=json.loads(row[9]) if row[9] else []
                )

        except Exception as e:
            logger.error(f"Failed to get cached reputation: {e}")
            return None

    def _cache_ip_reputation(self, reputation: IPReputation):
        """Cache IP reputation for 24 hours"""
        try:
            expires_at = datetime.now() + timedelta(hours=24)

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ip_reputation_cache
                    (ip, reputation_score, is_malicious, abuse_confidence, country,
                     asn, usage_type, reports, last_reported, categories, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (reputation.ip, reputation.reputation_score, reputation.is_malicious,
                      reputation.abuse_confidence, reputation.country, reputation.asn,
                      reputation.usage_type, reputation.reports,
                      reputation.last_reported.isoformat() if reputation.last_reported else None,
                      json.dumps(reputation.categories), expires_at))
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to cache reputation: {e}")

    def _check_local_threat_feed(self, value: str, indicator_type: str = 'ip') -> Optional[Dict[str, Any]]:
        """Check value against local threat feed"""
        indicator = self.get_threat_indicator(indicator_type, value)
        if indicator:
            return {
                'value': value,
                'is_malicious': indicator.confidence > 70,
                'threat_type': indicator.threat_type,
                'severity': indicator.severity,
                'confidence': indicator.confidence,
                'sources': indicator.sources
            }
        return None

    def import_threat_feed(self, feed_url: str, feed_name: str, feed_type: str = 'ip') -> int:
        """
        Import threat feed from URL

        Args:
            feed_url: URL of threat feed
            feed_name: Name of feed
            feed_type: Type of indicators in feed

        Returns:
            Number of indicators imported
        """
        try:
            logger.info(f"Importing threat feed: {feed_name} from {feed_url}")

            response = requests.get(feed_url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch feed: {response.status_code}")
                return 0

            # Parse feed (assuming one indicator per line, # for comments)
            indicators = []
            for line in response.text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    indicators.append(line)

            # Import indicators
            imported = 0
            for indicator in indicators:
                if self.add_threat_indicator(
                    indicator_type=feed_type,
                    value=indicator,
                    threat_type='malicious',
                    severity='medium',
                    confidence=75,
                    source=feed_name
                ):
                    imported += 1

            # Update feed metadata
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO threat_feeds
                    (feed_name, feed_url, feed_type, last_updated, indicator_count)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (feed_name, feed_url, feed_type, imported))
                conn.commit()

            logger.info(f"Imported {imported} indicators from {feed_name}")
            return imported

        except Exception as e:
            logger.error(f"Failed to import threat feed: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get threat intelligence statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Count indicators by type
                cursor = conn.execute("""
                    SELECT indicator_type, COUNT(*)
                    FROM threat_indicators
                    GROUP BY indicator_type
                """)
                indicators_by_type = dict(cursor.fetchall())

                # Count by severity
                cursor = conn.execute("""
                    SELECT severity, COUNT(*)
                    FROM threat_indicators
                    GROUP BY severity
                """)
                indicators_by_severity = dict(cursor.fetchall())

                # Count cached IPs
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM ip_reputation_cache
                    WHERE expires_at > CURRENT_TIMESTAMP
                """)
                cached_ips = cursor.fetchone()[0]

                # Count threat feeds
                cursor = conn.execute("""
                    SELECT COUNT(*), SUM(indicator_count)
                    FROM threat_feeds WHERE enabled = 1
                """)
                feeds_count, total_feed_indicators = cursor.fetchone()

                return {
                    'indicators_by_type': indicators_by_type,
                    'indicators_by_severity': indicators_by_severity,
                    'cached_ip_reputations': cached_ips,
                    'active_threat_feeds': feeds_count or 0,
                    'total_feed_indicators': total_feed_indicators or 0
                }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


# Predefined threat feeds (free, open-source)
THREAT_FEEDS = [
    {
        'name': 'Abuse.ch URLhaus',
        'url': 'https://urlhaus.abuse.ch/downloads/text_recent/',
        'type': 'url'
    },
    {
        'name': 'Emerging Threats Compromised IPs',
        'url': 'https://rules.emergingthreats.net/blockrules/compromised-ips.txt',
        'type': 'ip'
    },
    {
        'name': 'MalwareDomainList',
        'url': 'http://www.malwaredomainlist.com/hostslist/ip.txt',
        'type': 'ip'
    }
]
