"""
Training Pipeline for Sponge

Orchestrates the complete training workflow from data import to model deployment.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd

from .data_importer import DataImporter
from .model_trainer import ModelTrainer

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """Complete ML training pipeline"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Training Pipeline

        Args:
            config: Pipeline configuration
        """
        self.config = config or {}
        self.data_importer = DataImporter(config.get('importer', {}))
        self.model_trainer = ModelTrainer(
            model_dir=config.get('model_dir', 'models'),
            config=config.get('trainer', {})
        )
        self.pipeline_history = []

    def run_complete_training(self,
                             data_source: str,
                             source_type: str = 'file',
                             models_to_train: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run complete training pipeline

        Args:
            data_source: Path to data file or data dict
            source_type: Type of data source (file, cloudwatch, datadog, dynatrace)
            models_to_train: List of models to train (default: all)

        Returns:
            Pipeline results dictionary
        """
        logger.info(f"Starting training pipeline (source: {source_type})")

        results = {
            'source': data_source,
            'source_type': source_type,
            'models_trained': {},
            'errors': []
        }

        try:
            # Step 1: Import data
            logger.info("Step 1: Importing data")
            if source_type == 'file':
                df = self.data_importer.import_from_file(data_source)
            elif source_type == 'cloudwatch':
                df = self.data_importer.import_from_cloudwatch(data_source)
            elif source_type == 'datadog':
                df = self.data_importer.import_from_datadog(data_source)
            elif source_type == 'dynatrace':
                df = self.data_importer.import_from_dynatrace(data_source)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            results['records_imported'] = len(df)

            # Step 2: Validate data
            logger.info("Step 2: Validating data")
            validation = self.data_importer.validate_training_data(df)
            results['validation'] = validation

            if not validation['is_valid']:
                raise ValueError(f"Data validation failed: {validation.get('errors', [])}")

            # Step 3: Train models
            logger.info("Step 3: Training models")
            models_to_train = models_to_train or ['text_classifier', 'anomaly_detector', 'clustering']

            for model_type in models_to_train:
                try:
                    logger.info(f"Training {model_type}")
                    model_results = self._train_model(df, model_type)
                    results['models_trained'][model_type] = model_results
                except Exception as e:
                    logger.error(f"Error training {model_type}: {e}")
                    results['errors'].append({
                        'model_type': model_type,
                        'error': str(e)
                    })

            # Step 4: Save training history
            logger.info("Step 4: Saving training history")
            history_path = self.model_trainer.save_training_history()
            results['history_path'] = history_path

            results['success'] = True
            logger.info("Training pipeline completed successfully")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results['success'] = False
            results['error'] = str(e)

        self.pipeline_history.append(results)
        return results

    def _train_model(self, df: pd.DataFrame, model_type: str) -> Dict[str, Any]:
        """
        Train a specific model

        Args:
            df: Training data
            model_type: Type of model to train

        Returns:
            Training results
        """
        if model_type == 'text_classifier':
            # Check if we have labels
            if 'issue_type' in df.columns and df['issue_type'].notna().sum() > 0:
                return self.model_trainer.train_text_classifier(df)
            else:
                raise ValueError("No labeled data for text classification")

        elif model_type == 'anomaly_detector':
            # Find numeric columns
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
            if len(numeric_cols) == 0:
                raise ValueError("No numeric columns for anomaly detection")
            return self.model_trainer.train_anomaly_detector(df, numeric_cols)

        elif model_type == 'clustering':
            return self.model_trainer.train_clustering_model(df)

        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def train_on_monitoring_exports(self,
                                    export_dir: str,
                                    platform: str = 'auto') -> Dict[str, Any]:
        """
        Train models on exported monitoring data

        Args:
            export_dir: Directory containing exported data files
            platform: Platform type (auto, cloudwatch, datadog, dynatrace)

        Returns:
            Training results
        """
        logger.info(f"Training on monitoring exports from {export_dir}")

        export_path = Path(export_dir)
        if not export_path.exists():
            raise FileNotFoundError(f"Export directory not found: {export_dir}")

        # Find all data files
        data_files = list(export_path.glob('*.json')) + \
                    list(export_path.glob('*.csv')) + \
                    list(export_path.glob('*.parquet'))

        if len(data_files) == 0:
            raise ValueError(f"No data files found in {export_dir}")

        logger.info(f"Found {len(data_files)} data files")

        # Combine all data
        all_data = []
        for file_path in data_files:
            try:
                df = self.data_importer.import_from_file(str(file_path))
                all_data.append(df)
            except Exception as e:
                logger.warning(f"Failed to import {file_path}: {e}")

        if len(all_data) == 0:
            raise ValueError("No data could be imported")

        # Concatenate all dataframes
        combined_df = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined {len(combined_df)} total records")

        # Run training
        return self.run_complete_training(
            data_source=str(export_path),
            source_type='combined',
            models_to_train=['text_classifier', 'anomaly_detector', 'clustering']
        )

    def retrain_models(self, new_data_path: str,
                      models: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Retrain existing models with new data

        Args:
            new_data_path: Path to new training data
            models: List of models to retrain (default: all existing)

        Returns:
            Retraining results
        """
        logger.info(f"Retraining models with data from {new_data_path}")

        # Import new data
        df = self.data_importer.import_from_file(new_data_path)

        # Get existing models if not specified
        if models is None:
            models = self.model_trainer.list_models()

        results = {
            'models_retrained': {},
            'errors': []
        }

        for model_type in models:
            try:
                model_results = self.model_trainer.incremental_train(df, model_type)
                results['models_retrained'][model_type] = model_results
            except Exception as e:
                logger.error(f"Error retraining {model_type}: {e}")
                results['errors'].append({
                    'model_type': model_type,
                    'error': str(e)
                })

        return results

    def export_models(self, output_dir: str) -> Dict[str, str]:
        """
        Export all trained models to directory

        Args:
            output_dir: Output directory path

        Returns:
            Dictionary of model paths
        """
        logger.info(f"Exporting models to {output_dir}")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        model_paths = {}
        for model_type in self.model_trainer.list_models():
            model_info = self.model_trainer.get_model_info(model_type)
            if 'path' in model_info:
                model_paths[model_type] = model_info['path']

        logger.info(f"Exported {len(model_paths)} models")
        return model_paths

    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status

        Returns:
            Status dictionary
        """
        return {
            'trained_models': self.model_trainer.list_models(),
            'pipeline_runs': len(self.pipeline_history),
            'last_run': self.pipeline_history[-1] if self.pipeline_history else None
        }
