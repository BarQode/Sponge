"""
Knowledge Base Filtering System

Provides advanced filtering capabilities for knowledge base queries.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseFilter:
    """Advanced filtering for knowledge base"""

    def __init__(self):
        """Initialize filter"""
        self.filters = {}

    def add_filter(self, name: str, filter_func: Callable) -> 'KnowledgeBaseFilter':
        """
        Add a custom filter function

        Args:
            name: Filter name
            filter_func: Function that takes DataFrame and returns filtered DataFrame

        Returns:
            Self for chaining
        """
        self.filters[name] = filter_func
        return self

    def by_category(self, df: pd.DataFrame, categories: List[str]) -> pd.DataFrame:
        """
        Filter by category

        Args:
            df: Input DataFrame
            categories: List of categories to include

        Returns:
            Filtered DataFrame
        """
        if 'Category' not in df.columns:
            logger.warning("Category column not found")
            return df

        return df[df['Category'].isin(categories)]

    def by_severity(self, df: pd.DataFrame, severities: List[str]) -> pd.DataFrame:
        """
        Filter by severity level

        Args:
            df: Input DataFrame
            severities: List of severity levels (critical, high, medium, low)

        Returns:
            Filtered DataFrame
        """
        if 'Severity' not in df.columns:
            logger.warning("Severity column not found")
            return df

        return df[df['Severity'].isin(severities)]

    def by_date_range(self, df: pd.DataFrame,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Filter by date range

        Args:
            df: Input DataFrame
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Filtered DataFrame
        """
        if 'Timestamp' not in df.columns:
            logger.warning("Timestamp column not found")
            return df

        # Convert to datetime if needed
        if df['Timestamp'].dtype == 'object':
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

        filtered_df = df.copy()

        if start_date:
            filtered_df = filtered_df[filtered_df['Timestamp'] >= start_date]

        if end_date:
            filtered_df = filtered_df[filtered_df['Timestamp'] <= end_date]

        return filtered_df

    def by_frequency(self, df: pd.DataFrame,
                    min_frequency: Optional[int] = None,
                    max_frequency: Optional[int] = None) -> pd.DataFrame:
        """
        Filter by frequency

        Args:
            df: Input DataFrame
            min_frequency: Minimum frequency (inclusive)
            max_frequency: Maximum frequency (inclusive)

        Returns:
            Filtered DataFrame
        """
        if 'Frequency' not in df.columns:
            logger.warning("Frequency column not found")
            return df

        filtered_df = df.copy()

        if min_frequency is not None:
            filtered_df = filtered_df[filtered_df['Frequency'] >= min_frequency]

        if max_frequency is not None:
            filtered_df = filtered_df[filtered_df['Frequency'] <= max_frequency]

        return filtered_df

    def by_confidence(self, df: pd.DataFrame,
                     min_confidence: float = 0.0,
                     max_confidence: float = 1.0) -> pd.DataFrame:
        """
        Filter by confidence score

        Args:
            df: Input DataFrame
            min_confidence: Minimum confidence (0.0-1.0)
            max_confidence: Maximum confidence (0.0-1.0)

        Returns:
            Filtered DataFrame
        """
        if 'Confidence' not in df.columns:
            logger.warning("Confidence column not found")
            return df

        return df[
            (df['Confidence'] >= min_confidence) &
            (df['Confidence'] <= max_confidence)
        ]

    def by_source(self, df: pd.DataFrame, sources: List[str]) -> pd.DataFrame:
        """
        Filter by source

        Args:
            df: Input DataFrame
            sources: List of sources to include

        Returns:
            Filtered DataFrame
        """
        if 'Source' not in df.columns:
            logger.warning("Source column not found")
            return df

        return df[df['Source'].isin(sources)]

    def by_issue_type(self, df: pd.DataFrame, issue_types: List[str]) -> pd.DataFrame:
        """
        Filter by issue type

        Args:
            df: Input DataFrame
            issue_types: List of issue types to include

        Returns:
            Filtered DataFrame
        """
        if 'Issue_Type' not in df.columns:
            logger.warning("Issue_Type column not found")
            return df

        return df[df['Issue_Type'].isin(issue_types)]

    def by_keyword(self, df: pd.DataFrame,
                   keywords: List[str],
                   columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Filter by keyword search

        Args:
            df: Input DataFrame
            keywords: List of keywords to search for
            columns: Columns to search in (default: all string columns)

        Returns:
            Filtered DataFrame
        """
        if columns is None:
            columns = df.select_dtypes(include=['object']).columns.tolist()

        # Create mask for matching any keyword in any column
        mask = pd.Series([False] * len(df))

        for keyword in keywords:
            for col in columns:
                if col in df.columns:
                    mask |= df[col].astype(str).str.contains(
                        keyword, case=False, na=False
                    )

        return df[mask]

    def has_solution(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to only entries with solutions

        Args:
            df: Input DataFrame

        Returns:
            Filtered DataFrame
        """
        if 'Solution' not in df.columns:
            logger.warning("Solution column not found")
            return df

        return df[df['Solution'].notna() & (df['Solution'] != '')]

    def has_implementation_steps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to only entries with implementation steps

        Args:
            df: Input DataFrame

        Returns:
            Filtered DataFrame
        """
        if 'Implementation_Steps' not in df.columns:
            logger.warning("Implementation_Steps column not found")
            return df

        return df[df['Implementation_Steps'].notna() & (df['Implementation_Steps'] != '')]

    def recent(self, df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
        """
        Filter to recent entries

        Args:
            df: Input DataFrame
            days: Number of days to look back

        Returns:
            Filtered DataFrame
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.by_date_range(df, start_date=cutoff_date)

    def top_frequency(self, df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
        """
        Get top N most frequent issues

        Args:
            df: Input DataFrame
            n: Number of top entries to return

        Returns:
            Filtered DataFrame
        """
        if 'Frequency' not in df.columns:
            logger.warning("Frequency column not found")
            return df.head(n)

        return df.nlargest(n, 'Frequency')

    def apply_filters(self, df: pd.DataFrame,
                     filter_config: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply multiple filters based on configuration

        Args:
            df: Input DataFrame
            filter_config: Dictionary of filter configurations

        Returns:
            Filtered DataFrame

        Example:
            filter_config = {
                'categories': ['CPU', 'Memory'],
                'severities': ['critical', 'high'],
                'min_confidence': 0.7,
                'has_solution': True,
                'recent_days': 30
            }
        """
        filtered_df = df.copy()

        # Apply each filter
        if 'categories' in filter_config:
            filtered_df = self.by_category(filtered_df, filter_config['categories'])

        if 'severities' in filter_config:
            filtered_df = self.by_severity(filtered_df, filter_config['severities'])

        if 'date_range' in filter_config:
            filtered_df = self.by_date_range(
                filtered_df,
                filter_config['date_range'].get('start'),
                filter_config['date_range'].get('end')
            )

        if 'min_frequency' in filter_config or 'max_frequency' in filter_config:
            filtered_df = self.by_frequency(
                filtered_df,
                filter_config.get('min_frequency'),
                filter_config.get('max_frequency')
            )

        if 'min_confidence' in filter_config or 'max_confidence' in filter_config:
            filtered_df = self.by_confidence(
                filtered_df,
                filter_config.get('min_confidence', 0.0),
                filter_config.get('max_confidence', 1.0)
            )

        if 'sources' in filter_config:
            filtered_df = self.by_source(filtered_df, filter_config['sources'])

        if 'issue_types' in filter_config:
            filtered_df = self.by_issue_type(filtered_df, filter_config['issue_types'])

        if 'keywords' in filter_config:
            filtered_df = self.by_keyword(
                filtered_df,
                filter_config['keywords'],
                filter_config.get('search_columns')
            )

        if filter_config.get('has_solution', False):
            filtered_df = self.has_solution(filtered_df)

        if filter_config.get('has_implementation_steps', False):
            filtered_df = self.has_implementation_steps(filtered_df)

        if 'recent_days' in filter_config:
            filtered_df = self.recent(filtered_df, filter_config['recent_days'])

        if 'top_n' in filter_config:
            filtered_df = self.top_frequency(filtered_df, filter_config['top_n'])

        # Apply custom filters
        for filter_name, filter_func in self.filters.items():
            if filter_name in filter_config:
                filtered_df = filter_func(filtered_df, filter_config[filter_name])

        logger.info(f"Filters applied: {len(df)} -> {len(filtered_df)} records")
        return filtered_df

    def get_filter_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get summary of available filter options

        Args:
            df: Input DataFrame

        Returns:
            Summary dictionary
        """
        summary = {
            'total_records': len(df),
            'available_filters': {}
        }

        if 'Category' in df.columns:
            summary['available_filters']['categories'] = df['Category'].unique().tolist()

        if 'Severity' in df.columns:
            summary['available_filters']['severities'] = df['Severity'].unique().tolist()

        if 'Source' in df.columns:
            summary['available_filters']['sources'] = df['Source'].unique().tolist()

        if 'Issue_Type' in df.columns:
            summary['available_filters']['issue_types'] = df['Issue_Type'].unique().tolist()

        if 'Frequency' in df.columns:
            summary['available_filters']['frequency_range'] = {
                'min': int(df['Frequency'].min()) if not df['Frequency'].isna().all() else 0,
                'max': int(df['Frequency'].max()) if not df['Frequency'].isna().all() else 0
            }

        if 'Confidence' in df.columns:
            summary['available_filters']['confidence_range'] = {
                'min': float(df['Confidence'].min()) if not df['Confidence'].isna().all() else 0.0,
                'max': float(df['Confidence'].max()) if not df['Confidence'].isna().all() else 1.0
            }

        if 'Timestamp' in df.columns:
            timestamps = pd.to_datetime(df['Timestamp'], errors='coerce')
            summary['available_filters']['date_range'] = {
                'earliest': timestamps.min().isoformat() if not timestamps.isna().all() else None,
                'latest': timestamps.max().isoformat() if not timestamps.isna().all() else None
            }

        return summary
