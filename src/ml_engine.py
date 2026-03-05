"""
Production-Ready Machine Learning Engine for Root Cause Analysis.

This engine combines multiple ML algorithms:
1. Random Forest Classifier - Determines the correct fix approach for bugs
2. Linear Regression - Predicts error frequency with coefficient-based thresholds
3. DBSCAN Clustering - Groups similar log patterns
4. Isolation Forest - Detects anomalies in metrics

Designed for production deployment with comprehensive error handling and persistence.
"""

import numpy as np
import re
import logging
import json
import joblib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

# ML imports
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.model_selection import cross_val_score
from sklearn.metrics import f1_score

from src.config import ML_CONFIG

# Configure logging
logger = logging.getLogger(__name__)

# Model persistence paths
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

BUG_FIX_MODEL_PATH = MODEL_DIR / "bug_fix_classifier.pkl"
ERROR_FREQ_MODEL_PATH = MODEL_DIR / "error_frequency_regressor.pkl"
ANOMALY_MODEL_PATH = MODEL_DIR / "anomaly_detector.pkl"

# Fix action constants
FIX_ACTIONS = [
    "restart_service",
    "rollback_deployment",
    "apply_patch",
    "scale_resources",
    "change_config",
    "redeploy_container",
    "clear_cache",
    "rotate_credentials",
    "escalate_to_oncall",
    "ignore_transient"
]

# Severity mapping
SEVERITY_MAP = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1
}

# Implementation steps for each fix action
_FIX_STEPS = {
    "restart_service": [
        "Identify the affected service from the error logs",
        "Check service health status and resource usage",
        "Execute graceful restart: systemctl restart <service>",
        "Monitor startup logs for successful initialization",
        "Verify service endpoints are responding correctly",
        "Update runbook with restart timestamp and outcome"
    ],
    "rollback_deployment": [
        "Identify the deployment version causing issues",
        "Locate the previous stable version from deployment history",
        "Execute rollback: kubectl rollout undo deployment/<name>",
        "Monitor pod status until all replicas are healthy",
        "Run smoke tests to verify functionality",
        "Document rollback reason and notify stakeholders"
    ],
    "apply_patch": [
        "Identify the specific bug or vulnerability from error details",
        "Locate the patch file or commit containing the fix",
        "Test patch in staging environment first",
        "Apply patch: git apply <patch> or package update",
        "Run regression tests to ensure no side effects",
        "Deploy to production with monitoring enabled"
    ],
    "scale_resources": [
        "Analyze current resource utilization (CPU, memory, disk)",
        "Determine scaling requirements based on load patterns",
        "Execute scaling: kubectl scale deployment/<name> --replicas=<N>",
        "For vertical scaling, update resource limits in deployment spec",
        "Monitor performance metrics post-scaling",
        "Set up alerts if sustained high load continues"
    ],
    "change_config": [
        "Identify configuration parameter causing the issue",
        "Review documentation for correct parameter values",
        "Update config file or environment variables",
        "Validate configuration syntax before applying",
        "Apply changes: kubectl apply or service restart",
        "Monitor logs to confirm issue resolution"
    ],
    "redeploy_container": [
        "Check container image version and build logs",
        "Pull latest stable image from registry",
        "Delete existing pod: kubectl delete pod <name>",
        "Verify new pod starts successfully with correct image",
        "Check application logs for startup errors",
        "Run health checks to ensure readiness"
    ],
    "clear_cache": [
        "Identify cache system involved (Redis, Memcached, app-level)",
        "Determine cache keys affected by the error",
        "Execute cache clear: redis-cli FLUSHDB or app API call",
        "Monitor cache hit rates after clearing",
        "Verify application behavior returns to normal",
        "Consider cache warming if necessary for performance"
    ],
    "rotate_credentials": [
        "Identify compromised or expired credentials",
        "Generate new credentials with appropriate permissions",
        "Update secret stores: kubectl create secret or vault write",
        "Restart services that use the updated credentials",
        "Revoke old credentials from identity provider",
        "Verify services authenticate successfully with new creds"
    ],
    "escalate_to_oncall": [
        "Document all troubleshooting steps attempted",
        "Gather relevant logs, metrics, and error context",
        "Create incident ticket with severity and impact assessment",
        "Page oncall engineer via PagerDuty or similar",
        "Provide incident context and handoff notes",
        "Continue monitoring until oncall acknowledges"
    ],
    "ignore_transient": [
        "Verify error is not recurring or increasing in frequency",
        "Check if error matches known transient patterns",
        "Document the transient error in observability dashboard",
        "Set up monitoring alert if frequency exceeds threshold",
        "Log decision to ignore for audit trail",
        "Schedule periodic review of transient error rates"
    ]
}

# Category pattern recognition
_CATEGORY_PATTERNS = {
    "memory": r"(oom|out of memory|memory leak|heap|stack overflow)",
    "network": r"(timeout|connection refused|dns|socket|unreachable)",
    "disk": r"(disk full|no space left|io error|read-only filesystem)",
    "authentication": r"(auth|401|403|unauthorized|forbidden|token|credential)",
    "database": r"(deadlock|connection pool|sql|query timeout|transaction)",
    "performance": r"(slow|latency|response time|bottleneck|degraded)",
    "configuration": r"(config|misconfigured|invalid setting|wrong parameter)"
}


@dataclass
class FrequencyAlert:
    """Alert generated when error frequency exceeds threshold."""
    error_class: str
    current_count: int
    predicted_count: float
    threshold: float
    coefficient: float
    alert_level: str  # "warning", "critical"


@dataclass
class RCAResult:
    """Root Cause Analysis result with fix recommendation."""
    cluster_id: int
    pattern: str
    category: str
    severity: str
    frequency: int
    recommended_fix: str
    fix_confidence: float
    fix_alternatives: List[Dict[str, float]]
    frequency_alert: Optional[FrequencyAlert]
    predicted_count_next_hour: float
    implementation_steps: List[str]
    source: str  # "ml_model" or "rule_based"
    timestamp: str


def clean_log(log_text: str) -> str:
    """
    Preprocesses logs to generalize them for ML analysis.
    Replaces dynamic data (IPs, timestamps, IDs) with tokens.

    Args:
        log_text: Raw log message string

    Returns:
        Cleaned and normalized log message
    """
    if not log_text or not isinstance(log_text, str):
        return ""

    try:
        log_text = log_text.lower()

        # Replace dynamic values with tokens
        log_text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', log_text)
        log_text = re.sub(r'\b([0-9a-f]{1,4}:){7}[0-9a-f]{1,4}\b', '<IPV6>', log_text)
        log_text = re.sub(r'\b([0-9a-f]{2}:){5}[0-9a-f]{2}\b', '<MAC>', log_text)
        log_text = re.sub(r'\b0x[0-9a-f]+\b', '<HEX>', log_text)
        log_text = re.sub(
            r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
            '<UUID>',
            log_text
        )
        log_text = re.sub(
            r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?\b',
            '<TIMESTAMP>',
            log_text
        )
        log_text = re.sub(r'[/\\][\w/\\.-]+', '<PATH>', log_text)
        log_text = re.sub(r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b', '<EMAIL>', log_text)
        log_text = re.sub(r'https?://[^\s]+', '<URL>', log_text)
        log_text = re.sub(r'\b\d{4,}\b', '<BIGNUM>', log_text)  # Large numbers (IDs, ports)
        log_text = re.sub(r'\b\d+\b', '<NUM>', log_text)  # Generic numbers

        # Remove extra whitespace
        log_text = ' '.join(log_text.split())

        return log_text
    except Exception as e:
        logger.warning(f"Error cleaning log: {e}")
        return log_text.lower() if isinstance(log_text, str) else ""


class BugFixClassifier:
    """
    Random Forest Classifier to determine the correct fix approach for bugs.

    Maps error features (log text, severity, category) to recommended fix actions.
    Uses TF-IDF for text vectorization and engineered features for classification.
    """

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            min_samples_split=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        self.vectorizer = TfidfVectorizer(
            max_features=4000,
            ngram_range=(1, 2),
            min_df=2,
            stop_words='english'
        )
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        logger.info("BugFixClassifier initialized")

    def _extract_features(self, log_texts: List[str], severities: List[str],
                          categories: List[str]) -> np.ndarray:
        """Extract features from logs for classification."""
        # TF-IDF features
        if self.is_trained:
            text_features = self.vectorizer.transform(log_texts).toarray()
        else:
            text_features = self.vectorizer.fit_transform(log_texts).toarray()

        # Engineered features
        severity_scores = np.array([SEVERITY_MAP.get(s, 3) for s in severities]).reshape(-1, 1)

        # Text-based features
        log_lengths = np.array([len(log) for log in log_texts]).reshape(-1, 1)
        has_stack_trace = np.array([1 if 'traceback' in log or 'stack' in log else 0
                                    for log in log_texts]).reshape(-1, 1)
        has_memory_keyword = np.array([1 if 'memory' in log or 'oom' in log else 0
                                       for log in log_texts]).reshape(-1, 1)
        has_network_keyword = np.array([1 if 'timeout' in log or 'connection' in log else 0
                                        for log in log_texts]).reshape(-1, 1)
        has_disk_keyword = np.array([1 if 'disk' in log or 'space' in log else 0
                                     for log in log_texts]).reshape(-1, 1)

        # Combine all features
        features = np.hstack([
            text_features,
            severity_scores,
            log_lengths,
            has_stack_trace,
            has_memory_keyword,
            has_network_keyword,
            has_disk_keyword
        ])

        return features

    def train(self, log_texts: List[str], labels: List[str],
              categories: List[str], severities: List[str]) -> Dict[str, Any]:
        """
        Train the Random Forest classifier on labeled bug fix data.

        Args:
            log_texts: List of cleaned log messages
            labels: List of correct fix actions (from FIX_ACTIONS)
            categories: List of error categories
            severities: List of severity levels

        Returns:
            Training metrics dictionary
        """
        try:
            logger.info(f"Training BugFixClassifier on {len(log_texts)} samples")

            # Validate inputs
            if len(set([len(log_texts), len(labels), len(categories), len(severities)])) != 1:
                raise ValueError("All input lists must have the same length")

            # Clean logs
            cleaned_logs = [clean_log(log) for log in log_texts]

            # Extract features
            X = self._extract_features(cleaned_logs, severities, categories)

            # Encode labels
            y = self.label_encoder.fit_transform(labels)

            # Train model
            self.model.fit(X, y)
            self.is_trained = True

            # Cross-validation for evaluation
            cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='f1_weighted')

            # Save model
            joblib.dump({
                'model': self.model,
                'vectorizer': self.vectorizer,
                'label_encoder': self.label_encoder
            }, BUG_FIX_MODEL_PATH)

            logger.info(f"BugFixClassifier trained successfully. F1: {cv_scores.mean():.3f}")

            return {
                "status": "success",
                "samples": len(log_texts),
                "f1_score_mean": float(cv_scores.mean()),
                "f1_score_std": float(cv_scores.std()),
                "num_classes": len(self.label_encoder.classes_),
                "classes": list(self.label_encoder.classes_)
            }

        except Exception as e:
            logger.error(f"Error training BugFixClassifier: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def load(self) -> bool:
        """Load trained model from disk."""
        try:
            if BUG_FIX_MODEL_PATH.exists():
                data = joblib.load(BUG_FIX_MODEL_PATH)
                self.model = data['model']
                self.vectorizer = data['vectorizer']
                self.label_encoder = data['label_encoder']
                self.is_trained = True
                logger.info("BugFixClassifier loaded from disk")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading BugFixClassifier: {e}")
            return False

    def predict(self, log_text: str, severity: str = "medium") -> Dict[str, Any]:
        """
        Predict the recommended fix action for a bug.

        Args:
            log_text: Raw or cleaned log message
            severity: Severity level of the error

        Returns:
            Dictionary with recommended_fix, confidence, and alternatives
        """
        try:
            # Load model if not already loaded
            if not self.is_trained:
                if not self.load():
                    logger.warning("Model not trained, using rule-based fallback")
                    return self._rule_based_fallback(log_text, severity)

            # Clean and extract features
            cleaned = clean_log(log_text)
            X = self._extract_features([cleaned], [severity], ["unknown"])

            # Get predictions with probabilities
            probas = self.model.predict_proba(X)[0]
            predicted_idx = np.argmax(probas)
            confidence = float(probas[predicted_idx])

            # Get top 3 alternatives
            top_3_indices = np.argsort(probas)[-3:][::-1]
            alternatives = [
                {
                    "action": self.label_encoder.inverse_transform([idx])[0],
                    "probability": float(probas[idx])
                }
                for idx in top_3_indices
            ]

            recommended_fix = self.label_encoder.inverse_transform([predicted_idx])[0]

            return {
                "recommended_fix": recommended_fix,
                "confidence": confidence,
                "alternatives": alternatives,
                "source": "ml_model"
            }

        except Exception as e:
            logger.error(f"Error predicting fix: {e}")
            return self._rule_based_fallback(log_text, severity)

    def _rule_based_fallback(self, log_text: str, severity: str) -> Dict[str, Any]:
        """Fallback to rule-based fix recommendation when model unavailable."""
        log_lower = log_text.lower()

        # Rule-based logic
        if "oom" in log_lower or "out of memory" in log_lower:
            fix = "scale_resources"
        elif "timeout" in log_lower or "connection refused" in log_lower:
            fix = "restart_service"
        elif "disk full" in log_lower or "no space" in log_lower:
            fix = "clear_cache"
        elif "401" in log_lower or "403" in log_lower or "auth" in log_lower:
            fix = "rotate_credentials"
        elif "deadlock" in log_lower or "database" in log_lower:
            fix = "restart_service"
        elif severity in ["critical", "high"]:
            fix = "escalate_to_oncall"
        else:
            fix = "ignore_transient"

        return {
            "recommended_fix": fix,
            "confidence": 0.6,
            "alternatives": [{"action": fix, "probability": 0.6}],
            "source": "rule_based"
        }


class ErrorFrequencyRegressor:
    """
    Linear Regression model for error frequency prediction with coefficient-based thresholds.

    Equation: ŷ = β₀ + β₁·t + β₂·severity_weight + β₃·freq_indicator

    Alert fires when: ŷ > threshold_coefficient × historical_mean

    Coefficients (β values) represent:
    - β₀: Base error rate
    - β₁: Time trend (errors increasing/decreasing over time)
    - β₂: Severity impact on frequency
    - β₃: Frequency indicator (recent spike pattern)
    """

    def __init__(self):
        self.models: Dict[str, LinearRegression] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.error_history: Dict[str, List[Tuple[datetime, int, str]]] = defaultdict(list)
        self.threshold_coefficients = {
            "critical": 1.5,
            "high": 2.0,
            "medium": 3.0,
            "low": 5.0,
            "info": 10.0
        }
        logger.info("ErrorFrequencyRegressor initialized")

    def record(self, error_class: str, count: int, severity: str,
               timestamp: Optional[datetime] = None):
        """Record an error occurrence for frequency tracking."""
        if timestamp is None:
            timestamp = datetime.now()

        self.error_history[error_class].append((timestamp, count, severity))
        logger.debug(f"Recorded {count} occurrences of {error_class} ({severity})")

    def fit(self, error_class: str) -> Dict[str, Any]:
        """
        Fit linear regression model for a specific error class.

        Returns:
            Dictionary with coefficients β₀, β₁, β₂, β₃ and model metrics
        """
        try:
            history = self.error_history[error_class]

            if len(history) < 5:
                logger.warning(f"Insufficient data for {error_class}: {len(history)} points")
                return {"status": "insufficient_data", "samples": len(history)}

            # Prepare features
            timestamps = [h[0] for h in history]
            counts = np.array([h[1] for h in history])
            severities = [h[2] for h in history]

            # Convert timestamps to numeric (hours since first observation)
            base_time = timestamps[0]
            time_deltas = np.array([(t - base_time).total_seconds() / 3600 for t in timestamps])

            # Feature engineering
            severity_weights = np.array([SEVERITY_MAP.get(s, 3) for s in severities])

            # Frequency indicator: rolling 3-period average
            freq_indicators = []
            for i in range(len(counts)):
                if i < 2:
                    freq_indicators.append(counts[i])
                else:
                    freq_indicators.append(np.mean(counts[max(0, i-2):i+1]))
            freq_indicators = np.array(freq_indicators)

            # Build feature matrix
            X = np.column_stack([
                np.ones(len(counts)),  # Intercept term
                time_deltas,
                severity_weights,
                freq_indicators
            ])

            # Fit model
            model = LinearRegression()
            model.fit(X[:, 1:], counts)  # sklearn adds intercept automatically

            # Store model and scaler
            self.models[error_class] = model
            scaler = StandardScaler()
            scaler.fit(X[:, 1:])
            self.scalers[error_class] = scaler

            # Extract coefficients
            β0 = model.intercept_
            β1, β2, β3 = model.coef_

            # Save model
            joblib.dump({
                'models': self.models,
                'scalers': self.scalers,
                'error_history': dict(self.error_history)
            }, ERROR_FREQ_MODEL_PATH)

            logger.info(f"Fitted model for {error_class}: β0={β0:.2f}, β1={β1:.4f}, β2={β2:.2f}, β3={β3:.2f}")

            return {
                "status": "success",
                "error_class": error_class,
                "β0_intercept": float(β0),
                "β1_time_trend": float(β1),
                "β2_severity_weight": float(β2),
                "β3_frequency_indicator": float(β3),
                "samples": len(counts),
                "r_squared": float(model.score(X[:, 1:], counts))
            }

        except Exception as e:
            logger.error(f"Error fitting model for {error_class}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def predict_and_check(self, error_class: str,
                          horizon_minutes: float = 60.0) -> Optional[FrequencyAlert]:
        """
        Predict error frequency and check if it exceeds threshold.

        Args:
            error_class: Error identifier
            horizon_minutes: Prediction time horizon in minutes

        Returns:
            FrequencyAlert if threshold exceeded, None otherwise
        """
        try:
            if error_class not in self.models:
                logger.debug(f"No model for {error_class}, attempting to fit")
                result = self.fit(error_class)
                if result.get("status") != "success":
                    return None

            model = self.models[error_class]
            history = self.error_history[error_class]

            # Get recent severity
            recent_severity = history[-1][2]
            severity_weight = SEVERITY_MAP.get(recent_severity, 3)

            # Calculate time delta for prediction
            base_time = history[0][0]
            current_time = datetime.now()
            future_time = current_time + timedelta(minutes=horizon_minutes)
            time_delta = (future_time - base_time).total_seconds() / 3600

            # Recent frequency indicator
            recent_counts = [h[1] for h in history[-3:]]
            freq_indicator = np.mean(recent_counts)

            # Build prediction features
            X_pred = np.array([[time_delta, severity_weight, freq_indicator]])

            # Predict
            predicted_count = model.predict(X_pred)[0]

            # Calculate historical mean
            historical_counts = [h[1] for h in history]
            historical_mean = np.mean(historical_counts)

            # Get threshold coefficient for severity
            threshold_coef = self.threshold_coefficients.get(recent_severity, 3.0)
            threshold = threshold_coef * historical_mean

            # Determine alert level
            if predicted_count > threshold:
                if predicted_count > threshold * 2:
                    alert_level = "critical"
                else:
                    alert_level = "warning"

                logger.warning(f"Frequency alert for {error_class}: predicted={predicted_count:.1f}, "
                             f"threshold={threshold:.1f}")

                return FrequencyAlert(
                    error_class=error_class,
                    current_count=history[-1][1],
                    predicted_count=float(predicted_count),
                    threshold=float(threshold),
                    coefficient=float(threshold_coef),
                    alert_level=alert_level
                )

            return None

        except Exception as e:
            logger.error(f"Error predicting frequency for {error_class}: {e}")
            return None

    def get_coefficients(self, error_class: str) -> Dict[str, float]:
        """Get the regression coefficients for an error class."""
        if error_class not in self.models:
            return {}

        model = self.models[error_class]
        return {
            "β0_intercept": float(model.intercept_),
            "β1_time_trend": float(model.coef_[0]),
            "β2_severity_weight": float(model.coef_[1]),
            "β3_frequency_indicator": float(model.coef_[2])
        }

    def load(self) -> bool:
        """Load trained models from disk."""
        try:
            if ERROR_FREQ_MODEL_PATH.exists():
                data = joblib.load(ERROR_FREQ_MODEL_PATH)
                self.models = data['models']
                self.scalers = data['scalers']
                self.error_history = defaultdict(list, data['error_history'])
                logger.info(f"Loaded {len(self.models)} error frequency models")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading ErrorFrequencyRegressor: {e}")
            return False

    def fit_all(self) -> Dict[str, Any]:
        """Fit models for all error classes with sufficient data."""
        results = {}
        for error_class in self.error_history.keys():
            results[error_class] = self.fit(error_class)
        return results


class LogClusterEngine:
    """
    DBSCAN-based log clustering for pattern identification.
    Backward compatible with original functionality.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=2000,
            ngram_range=(1, 2),
            min_df=1
        )
        logger.info("LogClusterEngine initialized")

    def cluster(self, log_texts: List[str]) -> Dict[int, List[str]]:
        """
        Cluster similar logs using DBSCAN.

        Args:
            log_texts: List of raw log messages

        Returns:
            Dictionary mapping cluster_id to list of logs
        """
        try:
            if not log_texts:
                return {}

            # Clean logs
            cleaned = [clean_log(log) for log in log_texts]

            # Remove empty logs
            valid_indices = [i for i, log in enumerate(cleaned) if log.strip()]
            cleaned_valid = [cleaned[i] for i in valid_indices]
            logs_valid = [log_texts[i] for i in valid_indices]

            if len(cleaned_valid) < 2:
                return {0: logs_valid}

            # Vectorize
            vectors = self.vectorizer.fit_transform(cleaned_valid).toarray()

            # Cluster
            clustering = DBSCAN(
                eps=ML_CONFIG.get("clustering_eps", 0.45),
                min_samples=ML_CONFIG.get("clustering_min_samples", 2),
                metric='cosine'
            ).fit(vectors)

            # Group by cluster
            clusters = defaultdict(list)
            for label, log in zip(clustering.labels_, logs_valid):
                clusters[int(label)].append(log)

            logger.info(f"Clustered {len(log_texts)} logs into {len(clusters)} groups")

            return dict(clusters)

        except Exception as e:
            logger.error(f"Error clustering logs: {e}")
            return {0: log_texts}


class AnomalyDetector:
    """
    Isolation Forest for anomaly detection in metrics.
    """

    def __init__(self, contamination: float = 0.05):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_jobs=-1
        )
        self.is_fitted = False
        logger.info("AnomalyDetector initialized")

    def fit(self, X: np.ndarray):
        """Train anomaly detector on normal metrics."""
        self.model.fit(X)
        self.is_fitted = True
        logger.info(f"AnomalyDetector fitted on {len(X)} samples")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict anomalies (-1 for anomaly, 1 for normal)."""
        if not self.is_fitted:
            logger.warning("AnomalyDetector not fitted yet")
            return np.ones(len(X))
        return self.model.predict(X)

    def load(self) -> bool:
        """Load trained model from disk."""
        try:
            if ANOMALY_MODEL_PATH.exists():
                self.model = joblib.load(ANOMALY_MODEL_PATH)
                self.is_fitted = True
                logger.info("AnomalyDetector loaded from disk")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading AnomalyDetector: {e}")
            return False

    def save(self):
        """Save trained model to disk."""
        try:
            joblib.dump(self.model, ANOMALY_MODEL_PATH)
            logger.info("AnomalyDetector saved to disk")
        except Exception as e:
            logger.error(f"Error saving AnomalyDetector: {e}")


class HybridMLEngine:
    """
    Unified ML Engine combining all algorithms.

    Pipeline: Raw logs → DBSCAN clustering → Random Forest fix prediction →
              Linear Regression frequency analysis → Anomaly detection
    """

    def __init__(self):
        self.bug_fix_classifier = BugFixClassifier()
        self.error_freq_regressor = ErrorFrequencyRegressor()
        self.log_cluster_engine = LogClusterEngine()
        self.anomaly_detector = AnomalyDetector()

        # Try to load existing models
        self.bug_fix_classifier.load()
        self.error_freq_regressor.load()
        self.anomaly_detector.load()

        logger.info("HybridMLEngine initialized")

    def analyze_root_causes(self, log_texts: List[str],
                           severity: str = "medium") -> List[RCAResult]:
        """
        Comprehensive root cause analysis with ML-driven fix recommendations.

        Args:
            log_texts: List of raw log messages
            severity: Default severity level if not specified per log

        Returns:
            List of RCAResult objects with fix recommendations and predictions
        """
        try:
            if not log_texts:
                return []

            logger.info(f"Analyzing {len(log_texts)} logs for root causes")

            # Step 1: Cluster similar logs
            clusters = self.log_cluster_engine.cluster(log_texts)

            results = []
            for cluster_id, cluster_logs in clusters.items():
                if cluster_id == -1:  # Skip noise cluster
                    continue

                # Get representative log
                representative = cluster_logs[0]
                cleaned_rep = clean_log(representative)

                # Infer category from patterns
                category = "unknown"
                for cat, pattern in _CATEGORY_PATTERNS.items():
                    if re.search(pattern, cleaned_rep):
                        category = cat
                        break

                # Step 2: Predict fix using Random Forest
                fix_prediction = self.bug_fix_classifier.predict(cleaned_rep, severity)
                recommended_fix = fix_prediction["recommended_fix"]
                fix_confidence = fix_prediction["confidence"]
                alternatives = fix_prediction["alternatives"]

                # Step 3: Check error frequency and predict future occurrences
                error_class = f"{category}_{cluster_id}"
                self.error_freq_regressor.record(error_class, len(cluster_logs), severity)

                frequency_alert = self.error_freq_regressor.predict_and_check(error_class)

                # Get predicted count for next hour
                predicted_count = 0.0
                if error_class in self.error_freq_regressor.models:
                    alert = self.error_freq_regressor.predict_and_check(error_class, horizon_minutes=60)
                    if alert:
                        predicted_count = alert.predicted_count
                    else:
                        # No alert but still get prediction
                        model = self.error_freq_regressor.models[error_class]
                        history = self.error_freq_regressor.error_history[error_class]
                        if history:
                            base_time = history[0][0]
                            future_time = datetime.now() + timedelta(hours=1)
                            time_delta = (future_time - base_time).total_seconds() / 3600
                            severity_weight = SEVERITY_MAP.get(severity, 3)
                            recent_counts = [h[1] for h in history[-3:]]
                            freq_indicator = np.mean(recent_counts)
                            X_pred = np.array([[time_delta, severity_weight, freq_indicator]])
                            predicted_count = model.predict(X_pred)[0]

                # Get implementation steps
                implementation_steps = _FIX_STEPS.get(recommended_fix, [])

                results.append(RCAResult(
                    cluster_id=cluster_id,
                    pattern=cleaned_rep,
                    category=category,
                    severity=severity,
                    frequency=len(cluster_logs),
                    recommended_fix=recommended_fix,
                    fix_confidence=fix_confidence,
                    fix_alternatives=alternatives,
                    frequency_alert=frequency_alert,
                    predicted_count_next_hour=float(predicted_count),
                    implementation_steps=implementation_steps,
                    source=fix_prediction["source"],
                    timestamp=datetime.now().isoformat()
                ))

            # Sort by frequency
            results.sort(key=lambda x: x.frequency, reverse=True)

            logger.info(f"Identified {len(results)} root causes")

            return results

        except Exception as e:
            logger.error(f"Error analyzing root causes: {e}", exc_info=True)
            return []

    def train(self, log_texts: List[str], labels: List[str],
              severities: List[str], categories: List[str]) -> Dict[str, Any]:
        """
        Train all ML models on labeled data.

        Args:
            log_texts: List of log messages
            labels: List of correct fix actions
            severities: List of severity levels
            categories: List of error categories

        Returns:
            Training results dictionary
        """
        results = {}

        # Train Random Forest classifier
        rf_result = self.bug_fix_classifier.train(log_texts, labels, categories, severities)
        results['bug_fix_classifier'] = rf_result

        # Record data for frequency regressor
        for i, log in enumerate(log_texts):
            error_class = f"{categories[i]}_training"
            self.error_freq_regressor.record(error_class, 1, severities[i])

        # Fit frequency models
        freq_results = self.error_freq_regressor.fit_all()
        results['error_frequency_regressor'] = freq_results

        return results

    def train_on_knowledge_base(self, kb_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train models using existing knowledge base entries.

        Args:
            kb_entries: List of KB dictionaries with error_message, fix_action, severity, category

        Returns:
            Training results
        """
        log_texts = [entry.get("error_message", "") for entry in kb_entries]
        labels = [entry.get("fix_action", "ignore_transient") for entry in kb_entries]
        severities = [entry.get("severity", "medium") for entry in kb_entries]
        categories = [entry.get("category", "unknown") for entry in kb_entries]

        return self.train(log_texts, labels, severities, categories)


# Backward compatibility: expose the original class name
class LogRCAEngine(HybridMLEngine):
    """Backward compatible wrapper for HybridMLEngine."""

    def __init__(self):
        super().__init__()
        logger.info("LogRCAEngine (backward compatibility mode)")

    def clean_log(self, log_text: str) -> str:
        """Backward compatible clean_log method."""
        return clean_log(log_text)

    def vectorize(self, clean_logs: List[str]) -> np.ndarray:
        """Backward compatible vectorize method using TF-IDF."""
        if not clean_logs:
            return np.array([])
        return self.log_cluster_engine.vectorizer.fit_transform(clean_logs).toarray()

    def get_cluster_statistics(self, logs: List[str]) -> Dict[str, Any]:
        """Backward compatible cluster statistics."""
        clusters = self.log_cluster_engine.cluster(logs)
        total_clustered = sum(len(v) for k, v in clusters.items() if k != -1)

        return {
            "total_logs": len(logs),
            "total_clustered": total_clustered,
            "total_patterns": len([k for k in clusters.keys() if k != -1]),
            "top_pattern_count": max([len(v) for v in clusters.values()]) if clusters else 0,
            "clusters": clusters
        }
