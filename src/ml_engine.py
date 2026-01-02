"""
Machine Learning Engine for Root Cause Analysis.
Uses TensorFlow for semantic log clustering and pattern identification.
"""

import tensorflow as tf
from tensorflow.keras.layers import TextVectorization
import numpy as np
import re
import logging
from sklearn.cluster import DBSCAN
from collections import Counter
from typing import List, Dict, Any
from src.config import ML_CONFIG

# Configure logging
logger = logging.getLogger(__name__)


class LogRCAEngine:
    """
    Root Cause Analysis Engine using TensorFlow and unsupervised clustering.

    This engine:
    1. Cleans and normalizes log messages
    2. Converts text to TF-IDF vectors using TensorFlow
    3. Clusters similar errors using DBSCAN
    4. Identifies the most frequent error patterns (root causes)
    """

    def __init__(self):
        """Initialize the ML engine with TensorFlow text vectorizer."""
        try:
            # Initialize TensorFlow Text Vectorizer
            self.vectorizer = TextVectorization(
                max_tokens=ML_CONFIG["max_tokens"],
                output_mode=ML_CONFIG["output_mode"]
            )
            self.is_fitted = False
            logger.info("LogRCAEngine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LogRCAEngine: {e}")
            raise

    def clean_log(self, log_text: str) -> str:
        """
        Preprocesses logs to generalize them for Root Cause Analysis.
        Replaces dynamic data (IPs, timestamps, IDs) with tokens.

        Args:
            log_text: Raw log message string

        Returns:
            Cleaned and normalized log message
        """
        if not log_text or not isinstance(log_text, str):
            return ""

        try:
            # Convert to lowercase for consistency
            log_text = log_text.lower()

            # Replace IPv4 addresses
            log_text = re.sub(
                r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
                '<IP>',
                log_text
            )

            # Replace IPv6 addresses
            log_text = re.sub(
                r'\b([0-9a-f]{1,4}:){7}[0-9a-f]{1,4}\b',
                '<IPV6>',
                log_text
            )

            # Replace hexadecimal IDs
            log_text = re.sub(r'\b0x[0-9a-f]+\b', '<HEX>', log_text)

            # Replace UUIDs
            log_text = re.sub(
                r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b',
                '<UUID>',
                log_text
            )

            # Replace timestamps (various formats)
            log_text = re.sub(
                r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?\b',
                '<TIMESTAMP>',
                log_text
            )

            # Replace file paths (Unix and Windows)
            log_text = re.sub(r'[/\\][\w/\\.-]+', '<PATH>', log_text)

            # Replace email addresses
            log_text = re.sub(r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b', '<EMAIL>', log_text)

            # Replace URLs
            log_text = re.sub(r'https?://[^\s]+', '<URL>', log_text)

            # Replace generic numbers (after specific patterns)
            log_text = re.sub(r'\b\d+\b', '<NUM>', log_text)

            # Remove extra whitespace
            log_text = ' '.join(log_text.split())

            return log_text
        except Exception as e:
            logger.warning(f"Error cleaning log '{log_text[:50]}...': {e}")
            return log_text.lower() if isinstance(log_text, str) else ""

    def vectorize(self, clean_logs: List[str]) -> np.ndarray:
        """
        Converts text logs to numeric vectors using TF-IDF embedding.

        Args:
            clean_logs: List of cleaned log messages

        Returns:
            NumPy array of TF-IDF vectors
        """
        if not clean_logs:
            logger.warning("Empty log list provided for vectorization")
            return np.array([])

        try:
            # Filter out empty strings
            clean_logs = [log for log in clean_logs if log.strip()]

            if not clean_logs:
                logger.warning("All logs were empty after filtering")
                return np.array([])

            # Adapt vectorizer on first use
            if not self.is_fitted:
                logger.info(f"Fitting vectorizer on {len(clean_logs)} logs")
                self.vectorizer.adapt(clean_logs)
                self.is_fitted = True

            # Convert to TF-IDF vectors
            vectors = self.vectorizer(clean_logs).numpy()
            logger.debug(f"Vectorized {len(clean_logs)} logs to shape {vectors.shape}")

            return vectors
        except Exception as e:
            logger.error(f"Error during vectorization: {e}")
            raise

    def analyze_root_causes(self, logs: List[str]) -> List[Dict[str, Any]]:
        """
        Performs clustering to find the most frequent error patterns (Root Causes).

        Args:
            logs: List of raw log messages

        Returns:
            List of dictionaries containing root cause information, sorted by frequency
        """
        if not logs:
            logger.warning("No logs provided for analysis")
            return []

        try:
            logger.info(f"Analyzing {len(logs)} logs for root causes")

            # Clean all logs
            cleaned = [self.clean_log(log) for log in logs]

            # Filter out empty cleaned logs and track indices
            valid_indices = [i for i, log in enumerate(cleaned) if log.strip()]
            cleaned_valid = [cleaned[i] for i in valid_indices]
            logs_valid = [logs[i] for i in valid_indices]

            if not cleaned_valid:
                logger.warning("All logs were empty after cleaning")
                return []

            # Vectorize
            vectors = self.vectorize(cleaned_valid)

            if vectors.size == 0:
                logger.warning("Vectorization produced empty result")
                return []

            # Handle case with too few samples for clustering
            if len(cleaned_valid) < ML_CONFIG["clustering_min_samples"]:
                logger.info(f"Too few logs ({len(cleaned_valid)}) for clustering, treating as single group")
                return [{
                    "pattern_id": 0,
                    "count": len(cleaned_valid),
                    "representative_log": cleaned_valid[0],
                    "original_log_example": logs_valid[0],
                    "all_logs": logs_valid
                }]

            # Perform DBSCAN clustering
            # DBSCAN is ideal for logs: no predefined cluster count, handles noise
            logger.info("Performing DBSCAN clustering")
            clustering = DBSCAN(
                eps=ML_CONFIG["clustering_eps"],
                min_samples=ML_CONFIG["clustering_min_samples"],
                metric=ML_CONFIG["clustering_metric"]
            ).fit(vectors)

            labels = clustering.labels_

            # Count cluster frequencies
            counts = Counter(labels)
            logger.info(f"Found {len(counts)} clusters (including noise)")

            # Build results
            results = []
            for label, count in counts.items():
                if label == -1:
                    # Skip noise cluster in main results
                    logger.debug(f"Skipping noise cluster with {count} outliers")
                    continue

                # Get all indices for this cluster
                cluster_indices = np.where(labels == label)[0]

                # Get representative log (first occurrence)
                rep_idx = cluster_indices[0]

                # Collect all logs in this cluster
                cluster_logs = [logs_valid[idx] for idx in cluster_indices]

                results.append({
                    "pattern_id": int(label),
                    "count": count,
                    "representative_log": cleaned_valid[rep_idx],
                    "original_log_example": logs_valid[rep_idx],
                    "all_logs": cluster_logs
                })

            # Sort by frequency (highest count = primary root cause)
            results.sort(key=lambda x: x['count'], reverse=True)

            logger.info(f"Identified {len(results)} error patterns")

            return results

        except Exception as e:
            logger.error(f"Error during root cause analysis: {e}", exc_info=True)
            raise

    def get_cluster_statistics(self, logs: List[str]) -> Dict[str, Any]:
        """
        Generate statistical summary of log clustering.

        Args:
            logs: List of raw log messages

        Returns:
            Dictionary with clustering statistics
        """
        try:
            root_causes = self.analyze_root_causes(logs)

            total_clustered = sum(rc['count'] for rc in root_causes)

            return {
                "total_logs": len(logs),
                "total_clustered": total_clustered,
                "total_patterns": len(root_causes),
                "top_pattern_count": root_causes[0]['count'] if root_causes else 0,
                "patterns": root_causes
            }
        except Exception as e:
            logger.error(f"Error generating cluster statistics: {e}")
            return {
                "total_logs": len(logs),
                "error": str(e)
            }
