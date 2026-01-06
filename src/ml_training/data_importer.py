"""
Data Importer for ML Training

Imports and preprocesses data from monitoring platforms for ML model training.
"""

import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataImporter:
    """Import and preprocess training data from monitoring platforms"""

    SUPPORTED_FORMATS = ['json', 'csv', 'parquet', 'cloudwatch', 'datadog', 'dynatrace']

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DataImporter

        Args:
            config: Configuration dictionary with import settings
        """
        self.config = config or {}
        self.data_cache = {}

    def import_from_file(self, file_path: str, format_type: str = 'auto') -> pd.DataFrame:
        """
        Import training data from file

        Args:
            file_path: Path to data file
            format_type: Format type (auto, json, csv, parquet)

        Returns:
            DataFrame with imported data

        Raises:
            ValueError: If format is not supported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Auto-detect format
        if format_type == 'auto':
            format_type = path.suffix.lstrip('.')

        logger.info(f"Importing data from {file_path} (format: {format_type})")

        if format_type == 'json':
            return self._import_json(file_path)
        elif format_type == 'csv':
            return self._import_csv(file_path)
        elif format_type == 'parquet':
            return self._import_parquet(file_path)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def import_from_cloudwatch(self, data: List[Dict]) -> pd.DataFrame:
        """
        Import CloudWatch log data

        Args:
            data: List of CloudWatch log entries

        Returns:
            DataFrame with standardized format
        """
        logger.info(f"Importing {len(data)} CloudWatch entries")

        records = []
        for entry in data:
            record = {
                'timestamp': entry.get('timestamp'),
                'message': entry.get('message', ''),
                'log_stream': entry.get('logStreamName', ''),
                'log_group': entry.get('logGroupName', ''),
                'source': 'cloudwatch',
                'raw_data': json.dumps(entry)
            }
            records.append(record)

        df = pd.DataFrame(records)
        return self._standardize_dataframe(df)

    def import_from_datadog(self, data: List[Dict]) -> pd.DataFrame:
        """
        Import DataDog log data

        Args:
            data: List of DataDog log entries

        Returns:
            DataFrame with standardized format
        """
        logger.info(f"Importing {len(data)} DataDog entries")

        records = []
        for entry in data:
            record = {
                'timestamp': entry.get('timestamp'),
                'message': entry.get('message', ''),
                'service': entry.get('service', ''),
                'host': entry.get('host', ''),
                'status': entry.get('status', ''),
                'source': 'datadog',
                'raw_data': json.dumps(entry)
            }
            records.append(record)

        df = pd.DataFrame(records)
        return self._standardize_dataframe(df)

    def import_from_dynatrace(self, data: List[Dict]) -> pd.DataFrame:
        """
        Import Dynatrace log data

        Args:
            data: List of Dynatrace log entries

        Returns:
            DataFrame with standardized format
        """
        logger.info(f"Importing {len(data)} Dynatrace entries")

        records = []
        for entry in data:
            record = {
                'timestamp': entry.get('timestamp'),
                'message': entry.get('content', ''),
                'entity': entry.get('entityId', ''),
                'severity': entry.get('severity', ''),
                'source': 'dynatrace',
                'raw_data': json.dumps(entry)
            }
            records.append(record)

        df = pd.DataFrame(records)
        return self._standardize_dataframe(df)

    def _import_json(self, file_path: str) -> pd.DataFrame:
        """Import JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try to detect platform format
            if 'logEvents' in data:
                return self.import_from_cloudwatch(data['logEvents'])
            elif 'logs' in data:
                return self.import_from_datadog(data['logs'])
            else:
                df = pd.DataFrame([data])
        else:
            raise ValueError("Unsupported JSON structure")

        return self._standardize_dataframe(df)

    def _import_csv(self, file_path: str) -> pd.DataFrame:
        """Import CSV file"""
        df = pd.read_csv(file_path)
        return self._standardize_dataframe(df)

    def _import_parquet(self, file_path: str) -> pd.DataFrame:
        """Import Parquet file"""
        df = pd.read_parquet(file_path)
        return self._standardize_dataframe(df)

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize DataFrame to common format

        Required columns:
        - timestamp: Event timestamp
        - message: Log message or event description
        - source: Data source platform

        Args:
            df: Input DataFrame

        Returns:
            Standardized DataFrame
        """
        # Ensure required columns exist
        if 'timestamp' not in df.columns:
            df['timestamp'] = datetime.now()

        if 'message' not in df.columns:
            if 'content' in df.columns:
                df['message'] = df['content']
            else:
                df['message'] = ''

        if 'source' not in df.columns:
            df['source'] = 'unknown'

        # Convert timestamp to datetime
        if df['timestamp'].dtype == 'object':
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Add metadata columns if not present
        if 'issue_type' not in df.columns:
            df['issue_type'] = None
        if 'severity' not in df.columns:
            df['severity'] = None
        if 'label' not in df.columns:
            df['label'] = None

        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)

        logger.info(f"Standardized {len(df)} records")
        return df

    def export_training_data(self, df: pd.DataFrame, output_path: str,
                            format_type: str = 'parquet') -> None:
        """
        Export preprocessed training data

        Args:
            df: DataFrame to export
            output_path: Output file path
            format_type: Export format (parquet, csv, json)
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format_type == 'parquet':
            df.to_parquet(output_path, index=False)
        elif format_type == 'csv':
            df.to_csv(output_path, index=False)
        elif format_type == 'json':
            df.to_json(output_path, orient='records', indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

        logger.info(f"Exported {len(df)} records to {output_path}")

    def validate_training_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate training data quality

        Args:
            df: DataFrame to validate

        Returns:
            Validation report dictionary
        """
        report = {
            'total_records': len(df),
            'missing_timestamps': df['timestamp'].isna().sum(),
            'missing_messages': df['message'].isna().sum(),
            'empty_messages': (df['message'] == '').sum(),
            'date_range': {
                'start': df['timestamp'].min() if not df['timestamp'].isna().all() else None,
                'end': df['timestamp'].max() if not df['timestamp'].isna().all() else None
            },
            'sources': df['source'].value_counts().to_dict() if 'source' in df.columns else {},
            'labeled_records': df['label'].notna().sum() if 'label' in df.columns else 0,
            'is_valid': True
        }

        # Check validity
        if report['missing_timestamps'] > len(df) * 0.5:
            report['is_valid'] = False
            report['errors'] = report.get('errors', []) + ['Too many missing timestamps']

        if report['empty_messages'] > len(df) * 0.5:
            report['is_valid'] = False
            report['errors'] = report.get('errors', []) + ['Too many empty messages']

        logger.info(f"Validation report: {json.dumps(report, indent=2, default=str)}")
        return report
