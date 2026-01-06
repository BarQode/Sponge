"""
Enhanced Knowledge Base Storage

Extends the original storage with advanced features for user selection and management.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from ..storage import KnowledgeBase
from .filters import KnowledgeBaseFilter

logger = logging.getLogger(__name__)


class EnhancedKnowledgeBase(KnowledgeBase):
    """Enhanced knowledge base with filtering and selection"""

    def __init__(self, kb_file: str = "data/knowledge_base.xlsx"):
        """
        Initialize enhanced knowledge base

        Args:
            kb_file: Path to knowledge base file
        """
        super().__init__(kb_file)
        self.filter = KnowledgeBaseFilter()
        self.user_selections = []

    def search(self, filter_config: Dict[str, Any]) -> pd.DataFrame:
        """
        Search knowledge base with filters

        Args:
            filter_config: Filter configuration dictionary

        Returns:
            Filtered DataFrame
        """
        df = self.get_all()
        return self.filter.apply_filters(df, filter_config)

    def add_user_selection(self, error_pattern: str, selected: bool = True,
                          notes: Optional[str] = None) -> None:
        """
        Mark an entry as selected by user

        Args:
            error_pattern: Error pattern to mark
            selected: Whether it's selected (True) or deselected (False)
            notes: Optional user notes
        """
        selection = {
            'error_pattern': error_pattern,
            'selected': selected,
            'timestamp': datetime.now().isoformat(),
            'notes': notes
        }
        self.user_selections.append(selection)

        logger.info(f"User selection recorded: {error_pattern} -> {selected}")

    def get_selected_entries(self) -> pd.DataFrame:
        """
        Get all user-selected entries

        Returns:
            DataFrame of selected entries
        """
        if not self.user_selections:
            return pd.DataFrame()

        selected_patterns = [
            s['error_pattern'] for s in self.user_selections if s['selected']
        ]

        df = self.get_all()
        return df[df['Error_Pattern'].isin(selected_patterns)]

    def bulk_select(self, filter_config: Dict[str, Any],
                   action: str = 'select') -> int:
        """
        Bulk select/deselect entries matching filters

        Args:
            filter_config: Filter configuration
            action: 'select' or 'deselect'

        Returns:
            Number of entries affected
        """
        filtered_df = self.search(filter_config)

        selected = (action == 'select')
        count = 0

        for pattern in filtered_df['Error_Pattern']:
            self.add_user_selection(pattern, selected=selected)
            count += 1

        logger.info(f"Bulk {action}: {count} entries")
        return count

    def get_summary_stats(self, filter_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get summary statistics

        Args:
            filter_config: Optional filter configuration

        Returns:
            Statistics dictionary
        """
        if filter_config:
            df = self.search(filter_config)
        else:
            df = self.get_all()

        stats = {
            'total_entries': len(df),
            'by_category': {},
            'by_severity': {},
            'by_source': {},
            'with_solutions': 0,
            'with_implementation_steps': 0,
            'avg_confidence': 0.0,
            'avg_frequency': 0.0
        }

        if len(df) == 0:
            return stats

        # Category breakdown
        if 'Category' in df.columns:
            stats['by_category'] = df['Category'].value_counts().to_dict()

        # Severity breakdown
        if 'Severity' in df.columns:
            stats['by_severity'] = df['Severity'].value_counts().to_dict()

        # Source breakdown
        if 'Source' in df.columns:
            stats['by_source'] = df['Source'].value_counts().to_dict()

        # Solution stats
        if 'Solution' in df.columns:
            stats['with_solutions'] = df['Solution'].notna().sum()

        # Implementation steps stats
        if 'Implementation_Steps' in df.columns:
            stats['with_implementation_steps'] = df['Implementation_Steps'].notna().sum()

        # Confidence stats
        if 'Confidence' in df.columns:
            stats['avg_confidence'] = float(df['Confidence'].mean())

        # Frequency stats
        if 'Frequency' in df.columns:
            stats['avg_frequency'] = float(df['Frequency'].mean())
            stats['total_frequency'] = int(df['Frequency'].sum())

        return stats

    def deduplicate(self, similarity_threshold: float = 0.95) -> int:
        """
        Remove duplicate entries based on similarity

        Args:
            similarity_threshold: Similarity threshold (0.0-1.0)

        Returns:
            Number of duplicates removed
        """
        df = self.get_all()
        initial_count = len(df)

        if initial_count == 0:
            return 0

        # Simple deduplication based on error pattern
        df_dedup = df.drop_duplicates(subset=['Error_Pattern'], keep='first')

        # Save deduplicated data
        self.df = df_dedup
        self._save_db()

        removed = initial_count - len(df_dedup)
        logger.info(f"Deduplication: removed {removed} duplicates")

        return removed

    def merge_entries(self, pattern1: str, pattern2: str,
                     merge_strategy: str = 'combine') -> bool:
        """
        Merge two similar entries

        Args:
            pattern1: First error pattern
            pattern2: Second error pattern
            merge_strategy: 'combine' or 'keep_first' or 'keep_second'

        Returns:
            True if successful
        """
        df = self.get_all()

        entry1 = df[df['Error_Pattern'] == pattern1]
        entry2 = df[df['Error_Pattern'] == pattern2]

        if len(entry1) == 0 or len(entry2) == 0:
            logger.warning(f"One or both patterns not found")
            return False

        if merge_strategy == 'combine':
            # Combine frequencies
            merged_freq = entry1['Frequency'].iloc[0] + entry2['Frequency'].iloc[0]

            # Use higher confidence
            merged_conf = max(entry1['Confidence'].iloc[0], entry2['Confidence'].iloc[0])

            # Update first entry
            df.loc[df['Error_Pattern'] == pattern1, 'Frequency'] = merged_freq
            df.loc[df['Error_Pattern'] == pattern1, 'Confidence'] = merged_conf

            # Remove second entry
            df = df[df['Error_Pattern'] != pattern2]

        elif merge_strategy == 'keep_first':
            df = df[df['Error_Pattern'] != pattern2]

        elif merge_strategy == 'keep_second':
            df = df[df['Error_Pattern'] != pattern1]

        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")

        self.df = df
        self._save_db()

        logger.info(f"Merged entries: {pattern1} + {pattern2}")
        return True

    def archive_old_entries(self, days_old: int = 365,
                           archive_file: Optional[str] = None) -> int:
        """
        Archive old entries to separate file

        Args:
            days_old: Age threshold in days
            archive_file: Archive file path (optional)

        Returns:
            Number of entries archived
        """
        if archive_file is None:
            archive_file = str(Path(self.kb_file).parent / 'archive.xlsx')

        df = self.get_all()

        if 'Last_Updated' not in df.columns:
            logger.warning("No Last_Updated column found")
            return 0

        # Convert to datetime
        df['Last_Updated'] = pd.to_datetime(df['Last_Updated'], errors='coerce')
        cutoff_date = datetime.now() - pd.Timedelta(days=days_old)

        # Separate old and current entries
        old_entries = df[df['Last_Updated'] < cutoff_date]
        current_entries = df[df['Last_Updated'] >= cutoff_date]

        if len(old_entries) == 0:
            logger.info("No entries to archive")
            return 0

        # Save archive
        old_entries.to_excel(archive_file, index=False)

        # Update main database
        self.df = current_entries
        self._save_db()

        logger.info(f"Archived {len(old_entries)} entries to {archive_file}")
        return len(old_entries)

    def export_selected(self, output_file: str,
                       format_type: str = 'xlsx') -> int:
        """
        Export only user-selected entries

        Args:
            output_file: Output file path
            format_type: Format (xlsx, csv, json)

        Returns:
            Number of entries exported
        """
        df = self.get_selected_entries()

        if len(df) == 0:
            logger.warning("No selected entries to export")
            return 0

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format_type == 'xlsx':
            df.to_excel(output_file, index=False)
        elif format_type == 'csv':
            df.to_csv(output_file, index=False)
        elif format_type == 'json':
            df.to_json(output_file, orient='records', indent=2)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        logger.info(f"Exported {len(df)} selected entries to {output_file}")
        return len(df)

    def get_recommendations(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get recommendations for most impactful issues to address

        Args:
            top_n: Number of recommendations to return

        Returns:
            List of recommendation dictionaries
        """
        df = self.get_all()

        if len(df) == 0:
            return []

        # Score based on frequency, severity, and confidence
        severity_scores = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}

        if 'Severity' in df.columns:
            df['severity_score'] = df['Severity'].map(severity_scores).fillna(0)
        else:
            df['severity_score'] = 2

        if 'Frequency' in df.columns and 'Confidence' in df.columns:
            df['impact_score'] = (
                df['Frequency'] * df['severity_score'] * df['Confidence']
            )
        else:
            df['impact_score'] = df['severity_score']

        # Get top issues
        top_issues = df.nlargest(top_n, 'impact_score')

        recommendations = []
        for _, row in top_issues.iterrows():
            rec = {
                'error_pattern': row.get('Error_Pattern', ''),
                'category': row.get('Category', ''),
                'severity': row.get('Severity', ''),
                'frequency': int(row.get('Frequency', 0)),
                'confidence': float(row.get('Confidence', 0)),
                'impact_score': float(row.get('impact_score', 0)),
                'solution': row.get('Solution', ''),
                'implementation_steps': row.get('Implementation_Steps', '')
            }
            recommendations.append(rec)

        return recommendations
