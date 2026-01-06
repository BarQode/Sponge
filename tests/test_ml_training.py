"""
Tests for ML Training Module
"""

import pytest
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import tempfile

from src.ml_training.data_importer import DataImporter
from src.ml_training.model_trainer import ModelTrainer
from src.ml_training.training_pipeline import TrainingPipeline


class TestDataImporter:
    """Test DataImporter class"""

    @pytest.fixture
    def importer(self):
        """Create DataImporter instance"""
        return DataImporter()

    @pytest.fixture
    def sample_data(self):
        """Create sample training data"""
        return [
            {
                'timestamp': '2024-01-01T10:00:00',
                'message': 'ERROR: Memory leak detected',
                'source': 'cloudwatch'
            },
            {
                'timestamp': '2024-01-01T11:00:00',
                'message': 'WARNING: High CPU usage',
                'source': 'datadog'
            }
        ]

    def test_import_from_cloudwatch(self, importer, sample_data):
        """Test CloudWatch data import"""
        df = importer.import_from_cloudwatch(sample_data)

        assert len(df) == 2
        assert 'timestamp' in df.columns
        assert 'message' in df.columns
        assert 'source' in df.columns
        assert df['source'].iloc[0] == 'cloudwatch'

    def test_import_from_datadog(self, importer, sample_data):
        """Test DataDog data import"""
        df = importer.import_from_datadog(sample_data)

        assert len(df) == 2
        assert 'timestamp' in df.columns
        assert 'message' in df.columns

    def test_import_from_json(self, importer, sample_data, tmp_path):
        """Test JSON file import"""
        json_file = tmp_path / 'test_data.json'
        with open(json_file, 'w') as f:
            json.dump(sample_data, f)

        df = importer.import_from_file(str(json_file), 'json')

        assert len(df) == 2
        assert 'message' in df.columns

    def test_import_from_csv(self, importer, tmp_path):
        """Test CSV file import"""
        csv_file = tmp_path / 'test_data.csv'
        df_sample = pd.DataFrame({
            'timestamp': ['2024-01-01', '2024-01-02'],
            'message': ['Error 1', 'Error 2']
        })
        df_sample.to_csv(csv_file, index=False)

        df = importer.import_from_file(str(csv_file), 'csv')

        assert len(df) == 2
        assert 'message' in df.columns

    def test_standardize_dataframe(self, importer):
        """Test DataFrame standardization"""
        df = pd.DataFrame({
            'content': ['Error 1', 'Error 2'],
            'time': ['2024-01-01', '2024-01-02']
        })

        df_std = importer._standardize_dataframe(df)

        assert 'timestamp' in df_std.columns
        assert 'message' in df_std.columns
        assert 'source' in df_std.columns

    def test_validate_training_data(self, importer, sample_data):
        """Test data validation"""
        df = pd.DataFrame(sample_data)
        report = importer.validate_training_data(df)

        assert 'total_records' in report
        assert report['total_records'] == 2
        assert 'is_valid' in report

    def test_export_training_data(self, importer, sample_data, tmp_path):
        """Test data export"""
        df = pd.DataFrame(sample_data)
        output_file = tmp_path / 'export.parquet'

        importer.export_training_data(df, str(output_file), 'parquet')

        assert output_file.exists()


class TestModelTrainer:
    """Test ModelTrainer class"""

    @pytest.fixture
    def trainer(self, tmp_path):
        """Create ModelTrainer instance"""
        return ModelTrainer(model_dir=str(tmp_path / 'models'))

    @pytest.fixture
    def labeled_data(self):
        """Create labeled training data"""
        return pd.DataFrame({
            'message': [
                'Memory leak in process',
                'High CPU usage detected',
                'Memory usage is high',
                'CPU spike detected'
            ] * 30,  # Repeat to have enough samples
            'issue_type': ['memory', 'cpu', 'memory', 'cpu'] * 30
        })

    def test_train_text_classifier(self, trainer, labeled_data):
        """Test text classifier training"""
        result = trainer.train_text_classifier(labeled_data)

        assert 'accuracy' in result
        assert 'model_type' in result
        assert result['model_type'] == 'text_classifier'
        assert result['accuracy'] > 0

    def test_train_text_classifier_insufficient_data(self, trainer):
        """Test training with insufficient data"""
        small_df = pd.DataFrame({
            'message': ['Error 1', 'Error 2'],
            'issue_type': ['type1', 'type2']
        })

        with pytest.raises(ValueError, match="Insufficient labeled data"):
            trainer.train_text_classifier(small_df)

    def test_train_anomaly_detector(self, trainer):
        """Test anomaly detector training"""
        df = pd.DataFrame({
            'metric1': list(range(100)),
            'metric2': list(range(100, 200))
        })

        result = trainer.train_anomaly_detector(df, ['metric1', 'metric2'])

        assert 'anomaly_rate' in result
        assert 'model_type' in result
        assert result['model_type'] == 'anomaly_detector'

    def test_train_clustering_model(self, trainer):
        """Test clustering model training"""
        df = pd.DataFrame({
            'message': [f'Error message {i}' for i in range(100)]
        })

        result = trainer.train_clustering_model(df)

        assert 'n_clusters' in result
        assert 'model_type' in result
        assert result['model_type'] == 'clustering'

    def test_save_training_history(self, trainer, tmp_path):
        """Test saving training history"""
        trainer.training_history = [{'model': 'test', 'accuracy': 0.9}]

        output_file = tmp_path / 'history.json'
        path = trainer.save_training_history(str(output_file))

        assert Path(path).exists()

    def test_get_model_info(self, trainer, labeled_data):
        """Test getting model info"""
        trainer.train_text_classifier(labeled_data)

        info = trainer.get_model_info('text_classifier')

        assert 'version' in info
        assert 'path' in info

    def test_list_models(self, trainer, labeled_data):
        """Test listing models"""
        trainer.train_text_classifier(labeled_data)

        models = trainer.list_models()

        assert 'text_classifier' in models


class TestTrainingPipeline:
    """Test TrainingPipeline class"""

    @pytest.fixture
    def pipeline(self, tmp_path):
        """Create TrainingPipeline instance"""
        config = {'model_dir': str(tmp_path / 'models')}
        return TrainingPipeline(config)

    @pytest.fixture
    def training_data_file(self, tmp_path):
        """Create training data file"""
        data = [
            {
                'timestamp': '2024-01-01T10:00:00',
                'message': 'Memory leak detected',
                'issue_type': 'memory'
            } for _ in range(150)
        ]

        json_file = tmp_path / 'training_data.json'
        with open(json_file, 'w') as f:
            json.dump(data, f)

        return str(json_file)

    def test_run_complete_training(self, pipeline, training_data_file):
        """Test complete training pipeline"""
        result = pipeline.run_complete_training(
            training_data_file,
            source_type='file',
            models_to_train=['clustering']
        )

        assert 'success' in result
        assert 'records_imported' in result
        assert result['records_imported'] > 0

    def test_get_pipeline_status(self, pipeline):
        """Test getting pipeline status"""
        status = pipeline.get_pipeline_status()

        assert 'trained_models' in status
        assert 'pipeline_runs' in status
