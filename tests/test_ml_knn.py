"""
Comprehensive tests for K-Nearest Neighbor (KNN) Error Detector.

Tests cover:
- Model training and validation
- Prediction accuracy
- Anomaly detection
- Similar error finding
- Memory efficiency
- CPU performance
- Model persistence
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ml.knn_detector import KNNErrorDetector


class TestKNNDetector(unittest.TestCase):
    """Test KNN Error Detector functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = KNNErrorDetector(n_neighbors=3, max_features=100)

        # Sample training data
        self.train_messages = [
            "Database connection failed",
            "Failed to connect to database",
            "Connection timeout to DB",
            "Out of memory error",
            "Memory allocation failed",
            "Insufficient memory",
            "Network unreachable",
            "Connection refused",
            "Timeout connecting to server",
        ]

        self.train_labels = [
            "database_error",
            "database_error",
            "database_error",
            "memory_error",
            "memory_error",
            "memory_error",
            "network_error",
            "network_error",
            "network_error",
        ]

    def test_initialization(self):
        """Test KNN detector initialization."""
        self.assertEqual(self.detector.n_neighbors, 3)
        self.assertEqual(self.detector.max_features, 100)
        self.assertFalse(self.detector.is_trained)

    def test_training(self):
        """Test model training."""
        metrics = self.detector.train(self.train_messages, self.train_labels)

        self.assertTrue(self.detector.is_trained)
        self.assertIn('accuracy', metrics)
        self.assertIn('training_samples', metrics)
        self.assertEqual(metrics['training_samples'], 9)

    def test_prediction(self):
        """Test prediction on new messages."""
        self.detector.train(self.train_messages, self.train_labels, validate=False)

        test_messages = [
            "Database connection timeout",
            "Out of memory exception",
            "Network connection failed"
        ]

        predictions = self.detector.predict(test_messages)

        self.assertEqual(len(predictions), 3)
        self.assertIn('predicted_class', predictions[0])
        self.assertIn('confidence', predictions[0])

        # Check predictions make sense
        self.assertEqual(predictions[0]['predicted_class'], 'database_error')
        self.assertEqual(predictions[1]['predicted_class'], 'memory_error')
        self.assertEqual(predictions[2]['predicted_class'], 'network_error')

    def test_prediction_with_probabilities(self):
        """Test prediction with probability scores."""
        self.detector.train(self.train_messages, self.train_labels, validate=False)

        predictions = self.detector.predict(
            ["Database error occurred"],
            return_probabilities=True
        )

        self.assertIn('probabilities', predictions[0])
        probs = predictions[0]['probabilities']
        self.assertIsInstance(probs, dict)
        # Probabilities should sum to approximately 1
        total_prob = sum(probs.values())
        self.assertAlmostEqual(total_prob, 1.0, places=1)

    def test_predict_single(self):
        """Test single message prediction."""
        self.detector.train(self.train_messages, self.train_labels, validate=False)

        prediction = self.detector.predict_single("Database connection lost")

        self.assertIn('predicted_class', prediction)
        self.assertEqual(prediction['predicted_class'], 'database_error')

    def test_find_similar_errors(self):
        """Test finding similar errors."""
        self.detector.train(self.train_messages, self.train_labels, validate=False)

        similar = self.detector.find_similar_errors(
            "Database timeout error",
            n_similar=3
        )

        self.assertEqual(len(similar), 3)
        # Should return tuples of (index, similarity, category)
        self.assertEqual(len(similar[0]), 3)
        # All similar errors should be database errors
        for _, _, category in similar:
            self.assertEqual(category, 'database_error')

    def test_detect_anomalies(self):
        """Test anomaly detection."""
        self.detector.train(self.train_messages, self.train_labels, validate=False)

        test_messages = [
            "Database connection failed",  # Normal
            "Completely unknown weird error xyz123",  # Anomaly
            "Memory allocation error"  # Normal
        ]

        anomalies = self.detector.detect_anomalies(test_messages, threshold=0.6)

        # The unknown error should be detected as anomaly
        self.assertGreater(len(anomalies), 0)
        self.assertIn('anomaly_score', anomalies[0])

    def test_model_info(self):
        """Test getting model information."""
        self.detector.train(self.train_messages, self.train_labels, validate=False)

        info = self.detector.get_model_info()

        self.assertTrue(info['is_trained'])
        self.assertEqual(info['n_neighbors'], 3)
        self.assertEqual(info['n_classes'], 3)
        self.assertIn('database_error', info['classes'])

    def test_insufficient_training_data(self):
        """Test training with insufficient data."""
        # Training data smaller than k
        small_messages = ["Error 1", "Error 2"]
        small_labels = ["type1", "type2"]

        # Should not crash, but reduce k
        metrics = self.detector.train(small_messages, small_labels, validate=False)

        self.assertTrue(self.detector.is_trained)
        self.assertLessEqual(self.detector.n_neighbors, len(small_messages))

    def test_mismatched_data_length(self):
        """Test error handling for mismatched data."""
        with self.assertRaises(ValueError):
            self.detector.train(
                ["msg1", "msg2"],
                ["label1"]  # Mismatched length
            )

    def test_prediction_before_training(self):
        """Test prediction before training raises error."""
        with self.assertRaises(ValueError):
            self.detector.predict(["some message"])


class TestKNNPerformance(unittest.TestCase):
    """Test KNN detector performance characteristics."""

    def setUp(self):
        """Set up performance test fixtures."""
        self.detector = KNNErrorDetector(n_neighbors=5, max_features=500)

        # Generate larger dataset
        self.large_messages = []
        self.large_labels = []

        error_types = ['db_error', 'mem_error', 'net_error', 'disk_error', 'cpu_error']
        error_templates = {
            'db_error': "Database {} connection {}",
            'mem_error': "Memory {} allocation {}",
            'net_error': "Network {} timeout {}",
            'disk_error': "Disk {} full {}",
            'cpu_error': "CPU {} overload {}"
        }

        for error_type in error_types:
            for i in range(20):  # 20 samples per type
                msg = error_templates[error_type].format(
                    f"error_{i}",
                    f"failed_{i}"
                )
                self.large_messages.append(msg)
                self.large_labels.append(error_type)

    def test_training_performance(self):
        """Test training doesn't take too long."""
        import time

        start = time.time()
        self.detector.train(self.large_messages, self.large_labels, validate=False)
        duration = time.time() - start

        # Training should complete in reasonable time (< 5 seconds for 100 samples)
        self.assertLess(duration, 5.0)

    def test_prediction_performance(self):
        """Test prediction latency."""
        import time

        self.detector.train(self.large_messages, self.large_labels, validate=False)

        test_messages = ["Database connection error"] * 10

        start = time.time()
        predictions = self.detector.predict(test_messages)
        duration = time.time() - start

        # Prediction should be fast (< 1 second for 10 predictions)
        self.assertLess(duration, 1.0)
        self.assertEqual(len(predictions), 10)

    def test_memory_efficiency(self):
        """Test memory usage is reasonable."""
        import sys

        # Get initial memory size
        initial_size = sys.getsizeof(self.detector)

        # Train model
        self.detector.train(self.large_messages, self.large_labels, validate=False)

        # Get final memory size
        final_size = sys.getsizeof(self.detector)

        # Memory should not explode (< 10MB difference for this dataset)
        memory_diff = (final_size - initial_size) / (1024 * 1024)  # Convert to MB
        self.assertLess(memory_diff, 10.0)


class TestKNNModelPersistence(unittest.TestCase):
    """Test KNN model saving and loading."""

    def setUp(self):
        """Set up model persistence tests."""
        self.detector = KNNErrorDetector(n_neighbors=3)
        self.train_messages = [
            "Database error",
            "DB connection failed",
            "Memory error",
            "Out of memory"
        ]
        self.train_labels = ["db_error", "db_error", "mem_error", "mem_error"]

    def test_model_save_and_load(self):
        """Test saving and loading trained model."""
        import tempfile
        import os

        # Train model
        self.detector.train(self.train_messages, self.train_labels, validate=False)

        # Save model
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
            model_path = f.name

        try:
            self.detector.save_model(model_path)
            self.assertTrue(os.path.exists(model_path))

            # Load into new detector
            new_detector = KNNErrorDetector()
            new_detector.load_model(model_path)

            # Verify model works
            self.assertTrue(new_detector.is_trained)
            prediction = new_detector.predict_single("Database connection timeout")
            self.assertEqual(prediction['predicted_class'], 'db_error')

        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)

    def test_save_untrained_model_fails(self):
        """Test saving untrained model raises error."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.pkl') as f:
            with self.assertRaises(ValueError):
                self.detector.save_model(f.name)


if __name__ == '__main__':
    unittest.main()
