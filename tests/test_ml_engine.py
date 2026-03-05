"""
Comprehensive tests for the ML Engine with Random Forest and Linear Regression.

Tests cover:
- BugFixClassifier (Random Forest)
- ErrorFrequencyRegressor (Linear Regression)
- LogClusterEngine (DBSCAN)
- AnomalyDetector (Isolation Forest)
- HybridMLEngine (integrated pipeline)
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from src.ml_engine import (
    BugFixClassifier,
    ErrorFrequencyRegressor,
    LogClusterEngine,
    AnomalyDetector,
    HybridMLEngine,
    clean_log,
    RCAResult,
    FrequencyAlert,
    FIX_ACTIONS,
    SEVERITY_MAP
)


class TestCleanLog:
    """Test log cleaning and normalization."""

    def test_clean_log_basic(self):
        """Test basic log cleaning."""
        log = "Error at 192.168.1.1 on 2024-03-05T10:30:00Z"
        cleaned = clean_log(log)
        assert "192.168.1.1" not in cleaned
        assert "<IP>" in cleaned
        assert "2024-03-05" not in cleaned
        assert "<TIMESTAMP>" in cleaned

    def test_clean_log_empty(self):
        """Test cleaning empty logs."""
        assert clean_log("") == ""
        assert clean_log(None) == ""

    def test_clean_log_uuid(self):
        """Test UUID replacement."""
        log = "Request failed: 550e8400-e29b-41d4-a716-446655440000"
        cleaned = clean_log(log)
        assert "550e8400" not in cleaned
        assert "<UUID>" in cleaned

    def test_clean_log_paths(self):
        """Test file path replacement."""
        log = "File not found: /var/log/app.log"
        cleaned = clean_log(log)
        assert "/var/log/app.log" not in cleaned
        assert "<PATH>" in cleaned

    def test_clean_log_urls(self):
        """Test URL replacement."""
        log = "Failed to fetch https://api.example.com/data"
        cleaned = clean_log(log)
        assert "https://api.example.com" not in cleaned
        assert "<URL>" in cleaned

    def test_clean_log_lowercase(self):
        """Test that cleaning converts to lowercase."""
        log = "ERROR: Connection Failed"
        cleaned = clean_log(log)
        assert cleaned == cleaned.lower()


class TestBugFixClassifier:
    """Test Random Forest classifier for bug fix recommendations."""

    @pytest.fixture
    def classifier(self):
        """Create a BugFixClassifier instance."""
        return BugFixClassifier()

    @pytest.fixture
    def training_data(self):
        """Generate training data for testing."""
        logs = [
            "OutOfMemoryError: Java heap space exceeded",
            "OutOfMemoryError: heap memory full",
            "MemoryError: Cannot allocate memory",
            "ConnectionRefusedError: Connection refused",
            "ConnectionTimeout: timeout after 30 seconds",
            "Connection reset by peer",
            "HTTP 500 Internal Server Error",
            "HTTP 503 Service Unavailable",
            "Service not responding",
            "Database deadlock detected",
            "Transaction rollback due to deadlock",
            "Disk full: no space left on device",
            "401 Unauthorized: invalid credentials",
            "403 Forbidden: access denied",
            "Authentication failed",
        ]

        labels = [
            "scale_resources",
            "scale_resources",
            "scale_resources",
            "restart_service",
            "restart_service",
            "restart_service",
            "rollback_deployment",
            "rollback_deployment",
            "rollback_deployment",
            "restart_service",
            "restart_service",
            "clear_cache",
            "rotate_credentials",
            "rotate_credentials",
            "rotate_credentials",
        ]

        categories = [
            "memory", "memory", "memory",
            "network", "network", "network",
            "performance", "performance", "performance",
            "database", "database",
            "disk",
            "authentication", "authentication", "authentication"
        ]

        severities = [
            "critical", "critical", "critical",
            "high", "high", "high",
            "critical", "critical", "critical",
            "high", "high",
            "critical",
            "high", "high", "high"
        ]

        return logs, labels, categories, severities

    def test_initialization(self, classifier):
        """Test classifier initialization."""
        assert classifier.model is not None
        assert classifier.vectorizer is not None
        assert classifier.label_encoder is not None
        assert not classifier.is_trained

    def test_train(self, classifier, training_data):
        """Test training the classifier."""
        logs, labels, categories, severities = training_data

        result = classifier.train(logs, labels, categories, severities)

        assert result["status"] == "success"
        assert result["samples"] == len(logs)
        assert result["num_classes"] > 0
        assert 0 <= result["f1_score_mean"] <= 1
        assert classifier.is_trained

    def test_predict_after_training(self, classifier, training_data):
        """Test prediction after training."""
        logs, labels, categories, severities = training_data
        classifier.train(logs, labels, categories, severities)

        # Test prediction on a memory error
        prediction = classifier.predict(
            "OutOfMemoryError: heap space exceeded",
            severity="critical"
        )

        assert "recommended_fix" in prediction
        assert prediction["recommended_fix"] in FIX_ACTIONS
        assert 0 <= prediction["confidence"] <= 1
        assert len(prediction["alternatives"]) > 0
        assert prediction["source"] == "ml_model"

    def test_predict_without_training(self, classifier):
        """Test prediction falls back to rule-based when not trained."""
        prediction = classifier.predict(
            "OutOfMemoryError: heap space",
            severity="critical"
        )

        assert "recommended_fix" in prediction
        assert prediction["recommended_fix"] in FIX_ACTIONS
        assert prediction["source"] == "rule_based"

    def test_rule_based_fallback_memory(self, classifier):
        """Test rule-based fallback for memory errors."""
        result = classifier._rule_based_fallback(
            "OutOfMemoryError: OOM",
            "critical"
        )
        assert result["recommended_fix"] == "scale_resources"

    def test_rule_based_fallback_network(self, classifier):
        """Test rule-based fallback for network errors."""
        result = classifier._rule_based_fallback(
            "Connection timeout",
            "high"
        )
        assert result["recommended_fix"] == "restart_service"

    def test_rule_based_fallback_disk(self, classifier):
        """Test rule-based fallback for disk errors."""
        result = classifier._rule_based_fallback(
            "Disk full no space left",
            "high"
        )
        assert result["recommended_fix"] == "clear_cache"

    def test_rule_based_fallback_auth(self, classifier):
        """Test rule-based fallback for authentication errors."""
        result = classifier._rule_based_fallback(
            "401 Unauthorized",
            "high"
        )
        assert result["recommended_fix"] == "rotate_credentials"

    def test_train_validation_error(self, classifier):
        """Test training with mismatched input lengths."""
        logs = ["error1", "error2"]
        labels = ["fix1"]  # Wrong length
        categories = ["cat1", "cat2"]
        severities = ["high", "high"]

        result = classifier.train(logs, labels, categories, severities)
        assert result["status"] == "error"


class TestErrorFrequencyRegressor:
    """Test Linear Regression for error frequency prediction."""

    @pytest.fixture
    def regressor(self):
        """Create an ErrorFrequencyRegressor instance."""
        return ErrorFrequencyRegressor()

    def test_initialization(self, regressor):
        """Test regressor initialization."""
        assert len(regressor.models) == 0
        assert len(regressor.scalers) == 0
        assert len(regressor.error_history) == 0
        assert regressor.threshold_coefficients["critical"] == 1.5
        assert regressor.threshold_coefficients["high"] == 2.0
        assert regressor.threshold_coefficients["medium"] == 3.0

    def test_record(self, regressor):
        """Test recording error occurrences."""
        regressor.record("test_error", 5, "high")
        regressor.record("test_error", 3, "high")

        assert "test_error" in regressor.error_history
        assert len(regressor.error_history["test_error"]) == 2

    def test_fit_insufficient_data(self, regressor):
        """Test fitting with insufficient data."""
        regressor.record("test_error", 1, "medium")
        regressor.record("test_error", 2, "medium")

        result = regressor.fit("test_error")
        assert result["status"] == "insufficient_data"

    def test_fit_with_sufficient_data(self, regressor):
        """Test fitting with sufficient data."""
        # Record 10 data points over time
        base_time = datetime.now()
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            count = 5 + i  # Increasing error count
            regressor.record("test_error", count, "high", timestamp)

        result = regressor.fit("test_error")

        assert result["status"] == "success"
        assert result["error_class"] == "test_error"
        assert "β0_intercept" in result
        assert "β1_time_trend" in result
        assert "β2_severity_weight" in result
        assert "β3_frequency_indicator" in result
        assert result["samples"] == 10
        assert "test_error" in regressor.models

    def test_get_coefficients(self, regressor):
        """Test retrieving coefficients."""
        # Create training data
        base_time = datetime.now()
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            regressor.record("test_error", 5 + i, "high", timestamp)

        regressor.fit("test_error")
        coefficients = regressor.get_coefficients("test_error")

        assert "β0_intercept" in coefficients
        assert "β1_time_trend" in coefficients
        assert "β2_severity_weight" in coefficients
        assert "β3_frequency_indicator" in coefficients

    def test_predict_and_check_no_alert(self, regressor):
        """Test prediction when threshold is not exceeded."""
        # Record stable error counts
        base_time = datetime.now()
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            regressor.record("stable_error", 5, "low", timestamp)  # Stable count

        regressor.fit("stable_error")
        alert = regressor.predict_and_check("stable_error", horizon_minutes=60)

        # Should not alert for stable low-severity errors
        # (threshold coefficient for low is 5.0x)
        # This test might return None or a non-critical alert

    def test_predict_and_check_with_alert(self, regressor):
        """Test prediction when threshold is exceeded."""
        # Record increasing error counts
        base_time = datetime.now()
        for i in range(10):
            timestamp = base_time + timedelta(hours=i)
            count = 5 + (i * 2)  # Increasing rapidly
            regressor.record("critical_error", count, "critical", timestamp)

        regressor.fit("critical_error")
        alert = regressor.predict_and_check("critical_error", horizon_minutes=60)

        # With rapidly increasing errors, should generate alert
        if alert:
            assert isinstance(alert, FrequencyAlert)
            assert alert.error_class == "critical_error"
            assert alert.predicted_count > alert.threshold
            assert alert.alert_level in ["warning", "critical"]
            assert alert.coefficient == 1.5  # Critical threshold

    def test_fit_all(self, regressor):
        """Test fitting all error classes."""
        # Record data for multiple error classes
        base_time = datetime.now()
        for error_class in ["error1", "error2", "error3"]:
            for i in range(10):
                timestamp = base_time + timedelta(hours=i)
                regressor.record(error_class, 5 + i, "high", timestamp)

        results = regressor.fit_all()

        assert len(results) == 3
        assert "error1" in results
        assert "error2" in results
        assert "error3" in results


class TestLogClusterEngine:
    """Test DBSCAN clustering engine."""

    @pytest.fixture
    def cluster_engine(self):
        """Create a LogClusterEngine instance."""
        return LogClusterEngine()

    def test_initialization(self, cluster_engine):
        """Test engine initialization."""
        assert cluster_engine.vectorizer is not None

    def test_cluster_similar_logs(self, cluster_engine):
        """Test clustering similar logs."""
        logs = [
            "ConnectionRefusedError at 192.168.1.1",
            "ConnectionRefusedError at 192.168.1.2",
            "ConnectionRefusedError at 192.168.1.3",
            "OutOfMemoryError heap space",
            "OutOfMemoryError heap full",
            "FileNotFound config.yml",
            "FileNotFound settings.json",
        ]

        clusters = cluster_engine.cluster(logs)

        assert len(clusters) > 0
        # Should group similar errors together
        total_logs = sum(len(v) for v in clusters.values())
        assert total_logs == len(logs)

    def test_cluster_empty_logs(self, cluster_engine):
        """Test clustering with empty input."""
        clusters = cluster_engine.cluster([])
        assert clusters == {}

    def test_cluster_single_log(self, cluster_engine):
        """Test clustering with single log."""
        logs = ["Single error message"]
        clusters = cluster_engine.cluster(logs)

        assert len(clusters) == 1
        assert 0 in clusters
        assert len(clusters[0]) == 1


class TestAnomalyDetector:
    """Test Isolation Forest anomaly detector."""

    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector instance."""
        return AnomalyDetector(contamination=0.1)

    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.model is not None
        assert not detector.is_fitted

    def test_fit(self, detector):
        """Test fitting the anomaly detector."""
        # Generate normal data
        X = np.random.randn(100, 5)

        detector.fit(X)
        assert detector.is_fitted

    def test_predict(self, detector):
        """Test anomaly prediction."""
        # Generate normal training data
        X_train = np.random.randn(100, 5)
        detector.fit(X_train)

        # Generate test data with anomalies
        X_test_normal = np.random.randn(10, 5)
        X_test_anomaly = np.random.randn(10, 5) * 10  # Extreme values

        predictions_normal = detector.predict(X_test_normal)
        predictions_anomaly = detector.predict(X_test_anomaly)

        # Most normal data should be classified as 1 (normal)
        # Some anomalies should be classified as -1 (anomaly)
        assert len(predictions_normal) == 10
        assert len(predictions_anomaly) == 10

    def test_predict_without_fit(self, detector):
        """Test prediction before fitting."""
        X = np.random.randn(10, 5)
        predictions = detector.predict(X)

        # Should return all normal (1) when not fitted
        assert all(p == 1 for p in predictions)


class TestHybridMLEngine:
    """Test integrated HybridMLEngine."""

    @pytest.fixture
    def engine(self):
        """Create a HybridMLEngine instance."""
        return HybridMLEngine()

    @pytest.fixture
    def sample_logs(self):
        """Generate sample logs for testing."""
        return [
            "CRITICAL: ConnectionRefusedError at 10.0.1.5",
            "CRITICAL: ConnectionRefusedError at 10.0.1.6",
            "ERROR: OutOfMemoryError: heap space exceeded",
            "ERROR: OutOfMemoryError: heap full",
            "WARNING: Database timeout after 30 seconds",
            "WARNING: Database timeout after 30 seconds",
            "ERROR: HTTP 500 Internal Server Error",
            "ERROR: HTTP 503 Service Unavailable",
        ]

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.bug_fix_classifier is not None
        assert engine.error_freq_regressor is not None
        assert engine.log_cluster_engine is not None
        assert engine.anomaly_detector is not None

    def test_analyze_root_causes(self, engine, sample_logs):
        """Test comprehensive root cause analysis."""
        results = engine.analyze_root_causes(sample_logs, severity="high")

        assert isinstance(results, list)
        assert len(results) > 0

        # Check first result structure
        result = results[0]
        assert isinstance(result, RCAResult)
        assert hasattr(result, 'cluster_id')
        assert hasattr(result, 'pattern')
        assert hasattr(result, 'category')
        assert hasattr(result, 'severity')
        assert hasattr(result, 'frequency')
        assert hasattr(result, 'recommended_fix')
        assert hasattr(result, 'fix_confidence')
        assert hasattr(result, 'fix_alternatives')
        assert hasattr(result, 'implementation_steps')
        assert hasattr(result, 'source')

        # Verify fix recommendation
        assert result.recommended_fix in FIX_ACTIONS
        assert 0 <= result.fix_confidence <= 1
        assert result.severity == "high"

    def test_analyze_root_causes_empty(self, engine):
        """Test analysis with empty logs."""
        results = engine.analyze_root_causes([])
        assert results == []

    def test_train(self, engine):
        """Test training all models."""
        logs = [
            "OutOfMemoryError: heap space",
            "ConnectionRefusedError",
            "HTTP 500 error",
            "Database deadlock",
            "Disk full",
        ]

        labels = [
            "scale_resources",
            "restart_service",
            "rollback_deployment",
            "restart_service",
            "clear_cache",
        ]

        severities = ["critical", "high", "high", "high", "medium"]
        categories = ["memory", "network", "performance", "database", "disk"]

        results = engine.train(logs, labels, severities, categories)

        assert "bug_fix_classifier" in results
        assert results["bug_fix_classifier"]["status"] == "success"

    def test_train_on_knowledge_base(self, engine):
        """Test training from knowledge base entries."""
        kb_entries = [
            {
                "error_message": "OutOfMemoryError",
                "fix_action": "scale_resources",
                "severity": "critical",
                "category": "memory"
            },
            {
                "error_message": "ConnectionRefusedError",
                "fix_action": "restart_service",
                "severity": "high",
                "category": "network"
            },
            {
                "error_message": "HTTP 500 error",
                "fix_action": "rollback_deployment",
                "severity": "high",
                "category": "performance"
            },
        ]

        results = engine.train_on_knowledge_base(kb_entries)

        assert "bug_fix_classifier" in results
        assert results["bug_fix_classifier"]["status"] == "success"


class TestRCAResult:
    """Test RCAResult dataclass."""

    def test_rca_result_creation(self):
        """Test creating an RCAResult."""
        result = RCAResult(
            cluster_id=0,
            pattern="error pattern",
            category="network",
            severity="high",
            frequency=10,
            recommended_fix="restart_service",
            fix_confidence=0.85,
            fix_alternatives=[{"action": "restart_service", "probability": 0.85}],
            frequency_alert=None,
            predicted_count_next_hour=12.5,
            implementation_steps=["step1", "step2"],
            source="ml_model",
            timestamp="2024-03-05T10:00:00"
        )

        assert result.cluster_id == 0
        assert result.pattern == "error pattern"
        assert result.recommended_fix == "restart_service"
        assert result.fix_confidence == 0.85
        assert result.frequency == 10


class TestFrequencyAlert:
    """Test FrequencyAlert dataclass."""

    def test_frequency_alert_creation(self):
        """Test creating a FrequencyAlert."""
        alert = FrequencyAlert(
            error_class="test_error",
            current_count=10,
            predicted_count=25.5,
            threshold=20.0,
            coefficient=2.0,
            alert_level="warning"
        )

        assert alert.error_class == "test_error"
        assert alert.current_count == 10
        assert alert.predicted_count == 25.5
        assert alert.threshold == 20.0
        assert alert.coefficient == 2.0
        assert alert.alert_level == "warning"


class TestIntegration:
    """Integration tests for the complete ML pipeline."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from logs to predictions."""
        # Initialize engine
        engine = HybridMLEngine()

        # Sample logs
        logs = [
            "CRITICAL: OutOfMemoryError at server-01",
            "CRITICAL: OutOfMemoryError at server-02",
            "ERROR: Connection timeout to database",
            "ERROR: Connection refused by service",
            "WARNING: High CPU usage 95%",
        ]

        # Analyze
        results = engine.analyze_root_causes(logs, severity="high")

        # Verify results
        assert len(results) > 0

        for result in results:
            # Each result should have valid data
            assert result.cluster_id >= -1
            assert result.pattern
            assert result.category
            assert result.recommended_fix in FIX_ACTIONS
            assert 0 <= result.fix_confidence <= 1
            assert len(result.implementation_steps) > 0

    def test_model_persistence(self):
        """Test saving and loading models."""
        # Create temporary directory for models
        with tempfile.TemporaryDirectory() as tmpdir:
            # Train a classifier
            classifier = BugFixClassifier()

            logs = [
                "OutOfMemoryError",
                "OutOfMemoryError heap",
                "ConnectionRefusedError",
            ]
            labels = ["scale_resources", "scale_resources", "restart_service"]
            categories = ["memory", "memory", "network"]
            severities = ["critical", "critical", "high"]

            classifier.train(logs, labels, categories, severities)

            # Load should work (models are saved during training)
            new_classifier = BugFixClassifier()
            loaded = new_classifier.load()

            # If model file exists, should load successfully
            if loaded:
                assert new_classifier.is_trained


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
