"""
K-Nearest Neighbor (KNN) Algorithm for Error and Threat Detection

This module implements a production-ready KNN classifier for:
- Error pattern detection
- Threat classification
- Anomaly detection
- Log similarity matching

Features:
- Optimized for large datasets
- Memory-efficient implementation
- CPU-optimized distance calculations
- Configurable distance metrics (Euclidean, Manhattan, Cosine)
- Automatic feature scaling
- Cross-validation support
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from collections import Counter

logger = logging.getLogger(__name__)


class KNNErrorDetector:
    """
    K-Nearest Neighbor classifier for error and threat detection.

    Uses TF-IDF vectorization for log messages and KNN classification
    for pattern matching and threat detection.
    """

    def __init__(
        self,
        n_neighbors: int = 5,
        metric: str = 'euclidean',
        weights: str = 'distance',
        max_features: int = 2000
    ):
        """
        Initialize KNN Error Detector.

        Args:
            n_neighbors: Number of neighbors to use (default: 5)
            metric: Distance metric ('euclidean', 'manhattan', 'cosine')
            weights: Weight function ('uniform' or 'distance')
            max_features: Maximum number of TF-IDF features (default: 2000)
        """
        self.n_neighbors = n_neighbors
        self.metric = metric
        self.weights = weights
        self.max_features = max_features

        # Initialize models
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=2,  # Minimum document frequency
            max_df=0.95,  # Maximum document frequency (filter common words)
            strip_accents='unicode',
            lowercase=True,
            analyzer='word',
            stop_words='english'
        )

        self.scaler = StandardScaler(with_mean=False)  # Sparse matrix compatible

        self.classifier = KNeighborsClassifier(
            n_neighbors=n_neighbors,
            metric=metric,
            weights=weights,
            algorithm='auto',  # Auto-select best algorithm
            leaf_size=30,  # For tree-based algorithms
            n_jobs=-1  # Use all CPU cores
        )

        self.is_trained = False
        self.classes_ = []
        self.training_accuracy = 0.0

        logger.info(f"Initialized KNN Error Detector (k={n_neighbors}, metric={metric})")

    def train(
        self,
        messages: List[str],
        labels: List[str],
        validate: bool = True
    ) -> Dict[str, float]:
        """
        Train the KNN classifier.

        Args:
            messages: List of log messages
            labels: List of error/threat labels
            validate: Whether to perform validation split

        Returns:
            Training metrics dictionary
        """
        try:
            if len(messages) != len(labels):
                raise ValueError("Messages and labels must have same length")

            if len(messages) < self.n_neighbors:
                logger.warning(
                    f"Training data size ({len(messages)}) is smaller than k ({self.n_neighbors}). "
                    f"Reducing k to {len(messages) - 1}"
                )
                self.n_neighbors = max(1, len(messages) - 1)
                self.classifier.n_neighbors = self.n_neighbors

            logger.info(f"Training KNN classifier with {len(messages)} samples")

            # Vectorize messages
            X = self.vectorizer.fit_transform(messages)
            logger.info(f"TF-IDF vectorization: {X.shape[0]} samples, {X.shape[1]} features")

            # Scale features
            X_scaled = self.scaler.fit_transform(X)

            # Train classifier
            self.classifier.fit(X_scaled, labels)
            self.classes_ = list(set(labels))
            self.is_trained = True

            # Calculate training metrics
            metrics = {}
            if validate and len(messages) >= 10:
                # Simple validation split (80/20)
                split_idx = int(len(messages) * 0.8)
                X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
                y_train, y_val = labels[:split_idx], labels[split_idx:]

                # Retrain on training set only
                self.classifier.fit(X_train, y_train)

                # Validate
                y_pred = self.classifier.predict(X_val)
                metrics = {
                    'accuracy': accuracy_score(y_val, y_pred),
                    'precision': precision_score(y_val, y_pred, average='weighted', zero_division=0),
                    'recall': recall_score(y_val, y_pred, average='weighted', zero_division=0),
                    'f1_score': f1_score(y_val, y_pred, average='weighted', zero_division=0),
                    'training_samples': len(messages),
                    'features': X.shape[1],
                    'classes': len(self.classes_)
                }

                # Retrain on full dataset
                self.classifier.fit(X_scaled, labels)
            else:
                # No validation
                y_pred = self.classifier.predict(X_scaled)
                metrics = {
                    'accuracy': accuracy_score(labels, y_pred),
                    'training_samples': len(messages),
                    'features': X.shape[1],
                    'classes': len(self.classes_)
                }

            self.training_accuracy = metrics.get('accuracy', 0.0)
            logger.info(f"KNN training complete. Accuracy: {self.training_accuracy:.2%}")

            return metrics

        except Exception as e:
            logger.error(f"Error training KNN classifier: {e}")
            raise

    def predict(
        self,
        messages: List[str],
        return_probabilities: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Predict error/threat categories for messages.

        Args:
            messages: List of log messages to classify
            return_probabilities: Whether to include probability scores

        Returns:
            List of prediction dictionaries with:
                - predicted_class: The predicted category
                - confidence: Confidence score (0-1)
                - neighbors: List of k nearest neighbors (if requested)
                - probabilities: Class probabilities (if requested)
        """
        if not self.is_trained:
            raise ValueError("Classifier must be trained before prediction")

        try:
            # Vectorize and scale
            X = self.vectorizer.transform(messages)
            X_scaled = self.scaler.transform(X)

            # Predict
            predictions = self.classifier.predict(X_scaled)
            distances, indices = self.classifier.kneighbors(X_scaled)

            results = []
            for i, (pred, dist, idx) in enumerate(zip(predictions, distances, indices)):
                result = {
                    'predicted_class': pred,
                    'confidence': self._calculate_confidence(dist),
                    'nearest_neighbors': idx.tolist(),
                    'distances': dist.tolist()
                }

                if return_probabilities:
                    # Calculate probability as inverse distance weighted voting
                    result['probabilities'] = self._calculate_probabilities(idx, dist)

                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            raise

    def predict_single(
        self,
        message: str,
        return_probabilities: bool = False
    ) -> Dict[str, Any]:
        """
        Predict category for a single message.

        Args:
            message: Log message to classify
            return_probabilities: Whether to include probability scores

        Returns:
            Prediction dictionary
        """
        results = self.predict([message], return_probabilities)
        return results[0] if results else {}

    def find_similar_errors(
        self,
        message: str,
        n_similar: int = 5
    ) -> List[Tuple[int, float, str]]:
        """
        Find similar error messages in the training set.

        Args:
            message: Query message
            n_similar: Number of similar messages to return

        Returns:
            List of (index, similarity_score, category) tuples
        """
        if not self.is_trained:
            raise ValueError("Classifier must be trained before finding similar errors")

        try:
            # Vectorize and scale
            X = self.vectorizer.transform([message])
            X_scaled = self.scaler.transform(X)

            # Find neighbors
            distances, indices = self.classifier.kneighbors(
                X_scaled,
                n_neighbors=min(n_similar, len(self.classifier._y))
            )

            # Convert distances to similarity scores (1 - normalized distance)
            max_dist = max(distances[0]) if max(distances[0]) > 0 else 1.0
            similarities = [1.0 - (d / max_dist) for d in distances[0]]

            # Get categories for neighbors
            neighbor_labels = [self.classifier._y[idx] for idx in indices[0]]

            results = [
                (int(idx), float(sim), label)
                for idx, sim, label in zip(indices[0], similarities, neighbor_labels)
            ]

            return results

        except Exception as e:
            logger.error(f"Error finding similar errors: {e}")
            return []

    def detect_anomalies(
        self,
        messages: List[str],
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalous/unusual error messages.

        Messages with low confidence scores are considered anomalies.

        Args:
            messages: List of messages to check
            threshold: Confidence threshold (messages below this are anomalies)

        Returns:
            List of anomaly dictionaries
        """
        if not self.is_trained:
            raise ValueError("Classifier must be trained before anomaly detection")

        try:
            predictions = self.predict(messages)
            anomalies = []

            for i, (message, pred) in enumerate(zip(messages, predictions)):
                if pred['confidence'] < threshold:
                    anomalies.append({
                        'index': i,
                        'message': message,
                        'predicted_class': pred['predicted_class'],
                        'confidence': pred['confidence'],
                        'anomaly_score': 1.0 - pred['confidence']
                    })

            logger.info(f"Detected {len(anomalies)} anomalies out of {len(messages)} messages")
            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    def _calculate_confidence(self, distances: np.ndarray) -> float:
        """
        Calculate confidence score from neighbor distances.

        Uses inverse distance weighting: closer neighbors = higher confidence.
        """
        if len(distances) == 0:
            return 0.0

        # Inverse distance: confidence is higher when neighbors are closer
        # Add small epsilon to avoid division by zero
        epsilon = 1e-10
        inverse_distances = 1.0 / (distances + epsilon)

        # Normalize to 0-1 range
        confidence = np.mean(inverse_distances) / (1.0 + np.mean(inverse_distances))

        return float(confidence)

    def _calculate_probabilities(
        self,
        neighbor_indices: np.ndarray,
        distances: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate class probabilities from neighbor votes.

        Uses inverse distance weighted voting.
        """
        # Get labels for neighbors
        neighbor_labels = [self.classifier._y[idx] for idx in neighbor_indices]

        # Calculate inverse distance weights
        epsilon = 1e-10
        weights = 1.0 / (distances + epsilon)
        total_weight = np.sum(weights)

        # Weighted vote for each class
        class_votes = {}
        for label, weight in zip(neighbor_labels, weights):
            class_votes[label] = class_votes.get(label, 0.0) + weight

        # Normalize to probabilities
        probabilities = {
            label: float(votes / total_weight)
            for label, votes in class_votes.items()
        }

        return probabilities

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the trained model.

        Returns:
            Model information dictionary
        """
        return {
            'is_trained': self.is_trained,
            'n_neighbors': self.n_neighbors,
            'metric': self.metric,
            'weights': self.weights,
            'max_features': self.max_features,
            'n_classes': len(self.classes_),
            'classes': self.classes_,
            'training_accuracy': self.training_accuracy,
            'n_training_samples': len(self.classifier._y) if self.is_trained else 0
        }

    def save_model(self, filepath: str):
        """Save the trained model to disk."""
        import pickle

        if not self.is_trained:
            raise ValueError("Cannot save untrained model")

        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'scaler': self.scaler,
                'classifier': self.classifier,
                'classes_': self.classes_,
                'config': {
                    'n_neighbors': self.n_neighbors,
                    'metric': self.metric,
                    'weights': self.weights,
                    'max_features': self.max_features
                }
            }

            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"Model saved to {filepath}")

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            raise

    def load_model(self, filepath: str):
        """Load a trained model from disk."""
        import pickle

        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)

            self.vectorizer = model_data['vectorizer']
            self.scaler = model_data['scaler']
            self.classifier = model_data['classifier']
            self.classes_ = model_data['classes_']

            config = model_data['config']
            self.n_neighbors = config['n_neighbors']
            self.metric = config['metric']
            self.weights = config['weights']
            self.max_features = config['max_features']

            self.is_trained = True

            logger.info(f"Model loaded from {filepath}")

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
