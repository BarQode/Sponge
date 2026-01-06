"""
Model Trainer for Sponge ML Models

Trains ML models on imported monitoring data.
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ModelTrainer:
    """Train and manage ML models for log analysis"""

    def __init__(self, model_dir: str = 'models', config: Optional[Dict[str, Any]] = None):
        """
        Initialize ModelTrainer

        Args:
            model_dir: Directory to save trained models
            config: Training configuration
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or self._default_config()
        self.models = {}
        self.training_history = []

    def _default_config(self) -> Dict[str, Any]:
        """Get default training configuration"""
        return {
            'batch_size': 32,
            'epochs': 10,
            'learning_rate': 0.001,
            'validation_split': 0.2,
            'early_stopping_patience': 3,
            'min_samples_for_training': 100,
            'max_features': 10000,
            'embedding_dim': 128,
            'lstm_units': 64,
            'dropout_rate': 0.3
        }

    def train_text_classifier(self, df: pd.DataFrame,
                              target_column: str = 'issue_type',
                              text_column: str = 'message') -> Dict[str, Any]:
        """
        Train text classification model

        Args:
            df: Training DataFrame
            target_column: Column containing labels
            text_column: Column containing text data

        Returns:
            Training results dictionary
        """
        logger.info(f"Training text classifier on {len(df)} samples")

        # Check if we have enough labeled data
        labeled_df = df[df[target_column].notna()]
        if len(labeled_df) < self.config['min_samples_for_training']:
            raise ValueError(
                f"Insufficient labeled data: {len(labeled_df)} samples "
                f"(minimum: {self.config['min_samples_for_training']})"
            )

        # Import here to avoid loading if not needed
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import classification_report, accuracy_score
        except ImportError:
            raise ImportError("scikit-learn is required for training")

        # Prepare data
        X = labeled_df[text_column].fillna('').astype(str)
        y = labeled_df[target_column]

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config['validation_split'], random_state=42
        )

        # Vectorize text
        vectorizer = TfidfVectorizer(
            max_features=self.config['max_features'],
            ngram_range=(1, 3),
            min_df=2
        )
        X_train_vec = vectorizer.fit_transform(X_train)
        X_test_vec = vectorizer.transform(X_test)

        # Train classifier
        classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=20,
            random_state=42,
            n_jobs=-1
        )
        classifier.fit(X_train_vec, y_train)

        # Evaluate
        y_pred = classifier.predict(X_test_vec)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)

        # Save model
        model_version = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = self.model_dir / f'text_classifier_{model_version}.pkl'
        vectorizer_path = self.model_dir / f'vectorizer_{model_version}.pkl'

        with open(model_path, 'wb') as f:
            pickle.dump(classifier, f)
        with open(vectorizer_path, 'wb') as f:
            pickle.dump(vectorizer, f)

        # Store in memory
        self.models['text_classifier'] = {
            'model': classifier,
            'vectorizer': vectorizer,
            'version': model_version,
            'path': str(model_path)
        }

        results = {
            'model_type': 'text_classifier',
            'version': model_version,
            'accuracy': accuracy,
            'classification_report': report,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'model_path': str(model_path),
            'vectorizer_path': str(vectorizer_path),
            'timestamp': datetime.now().isoformat()
        }

        self.training_history.append(results)
        logger.info(f"Text classifier trained successfully (accuracy: {accuracy:.3f})")

        return results

    def train_anomaly_detector(self, df: pd.DataFrame,
                               metric_columns: List[str]) -> Dict[str, Any]:
        """
        Train anomaly detection model

        Args:
            df: Training DataFrame
            metric_columns: Columns containing numeric metrics

        Returns:
            Training results dictionary
        """
        logger.info(f"Training anomaly detector on {len(df)} samples")

        try:
            from sklearn.ensemble import IsolationForest
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            raise ImportError("scikit-learn is required for training")

        # Prepare data
        X = df[metric_columns].fillna(0).values

        if len(X) < self.config['min_samples_for_training']:
            raise ValueError(f"Insufficient data: {len(X)} samples")

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train Isolation Forest
        detector = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        detector.fit(X_scaled)

        # Predict on training data
        predictions = detector.predict(X_scaled)
        anomaly_count = (predictions == -1).sum()
        anomaly_rate = anomaly_count / len(predictions)

        # Save model
        model_version = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = self.model_dir / f'anomaly_detector_{model_version}.pkl'
        scaler_path = self.model_dir / f'anomaly_scaler_{model_version}.pkl'

        with open(model_path, 'wb') as f:
            pickle.dump(detector, f)
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)

        # Store in memory
        self.models['anomaly_detector'] = {
            'model': detector,
            'scaler': scaler,
            'version': model_version,
            'path': str(model_path)
        }

        results = {
            'model_type': 'anomaly_detector',
            'version': model_version,
            'anomaly_rate': anomaly_rate,
            'anomaly_count': int(anomaly_count),
            'training_samples': len(X),
            'metric_columns': metric_columns,
            'model_path': str(model_path),
            'scaler_path': str(scaler_path),
            'timestamp': datetime.now().isoformat()
        }

        self.training_history.append(results)
        logger.info(f"Anomaly detector trained (anomaly rate: {anomaly_rate:.3f})")

        return results

    def train_clustering_model(self, df: pd.DataFrame,
                               text_column: str = 'message') -> Dict[str, Any]:
        """
        Train clustering model for log grouping

        Args:
            df: Training DataFrame
            text_column: Column containing text data

        Returns:
            Training results dictionary
        """
        logger.info(f"Training clustering model on {len(df)} samples")

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.cluster import DBSCAN
        except ImportError:
            raise ImportError("scikit-learn is required for training")

        # Prepare data
        X = df[text_column].fillna('').astype(str)

        if len(X) < self.config['min_samples_for_training']:
            raise ValueError(f"Insufficient data: {len(X)} samples")

        # Vectorize text
        vectorizer = TfidfVectorizer(
            max_features=self.config['max_features'],
            ngram_range=(1, 2),
            min_df=2
        )
        X_vec = vectorizer.fit_transform(X)

        # Train DBSCAN
        clusterer = DBSCAN(
            eps=0.5,
            min_samples=2,
            metric='cosine',
            n_jobs=-1
        )
        labels = clusterer.fit_predict(X_vec)

        # Analyze clusters
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        # Save model
        model_version = datetime.now().strftime('%Y%m%d_%H%M%S')
        vectorizer_path = self.model_dir / f'cluster_vectorizer_{model_version}.pkl'

        with open(vectorizer_path, 'wb') as f:
            pickle.dump(vectorizer, f)

        # Store in memory
        self.models['clustering'] = {
            'vectorizer': vectorizer,
            'version': model_version,
            'eps': 0.5,
            'min_samples': 2
        }

        results = {
            'model_type': 'clustering',
            'version': model_version,
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'training_samples': len(X),
            'vectorizer_path': str(vectorizer_path),
            'timestamp': datetime.now().isoformat()
        }

        self.training_history.append(results)
        logger.info(f"Clustering model trained ({n_clusters} clusters found)")

        return results

    def incremental_train(self, df: pd.DataFrame, model_type: str) -> Dict[str, Any]:
        """
        Perform incremental training on existing model

        Args:
            df: New training data
            model_type: Type of model to update

        Returns:
            Training results
        """
        logger.info(f"Incremental training for {model_type}")

        if model_type not in self.models:
            raise ValueError(f"Model '{model_type}' not found. Train initial model first.")

        # For now, retrain from scratch
        # In production, implement proper incremental learning
        if model_type == 'text_classifier':
            return self.train_text_classifier(df)
        elif model_type == 'anomaly_detector':
            metric_cols = [col for col in df.columns if df[col].dtype in [np.float64, np.int64]]
            return self.train_anomaly_detector(df, metric_cols)
        elif model_type == 'clustering':
            return self.train_clustering_model(df)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def load_model(self, model_path: str, model_type: str) -> None:
        """
        Load pretrained model

        Args:
            model_path: Path to model file
            model_type: Type of model
        """
        logger.info(f"Loading {model_type} model from {model_path}")

        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        self.models[model_type] = {
            'model': model,
            'path': model_path,
            'loaded_at': datetime.now().isoformat()
        }

    def save_training_history(self, output_path: Optional[str] = None) -> str:
        """
        Save training history to file

        Args:
            output_path: Optional custom output path

        Returns:
            Path to saved history file
        """
        if output_path is None:
            output_path = self.model_dir / 'training_history.json'

        with open(output_path, 'w') as f:
            json.dump(self.training_history, f, indent=2, default=str)

        logger.info(f"Training history saved to {output_path}")
        return str(output_path)

    def get_model_info(self, model_type: str) -> Dict[str, Any]:
        """
        Get information about a trained model

        Args:
            model_type: Type of model

        Returns:
            Model information dictionary
        """
        if model_type not in self.models:
            raise ValueError(f"Model '{model_type}' not found")

        model_info = self.models[model_type].copy()
        # Remove the actual model object from info
        if 'model' in model_info:
            model_info['model'] = '<loaded>'
        if 'vectorizer' in model_info:
            model_info['vectorizer'] = '<loaded>'
        if 'scaler' in model_info:
            model_info['scaler'] = '<loaded>'

        return model_info

    def list_models(self) -> List[str]:
        """
        List all available models

        Returns:
            List of model types
        """
        return list(self.models.keys())
