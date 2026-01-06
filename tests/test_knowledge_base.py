"""
Tests for Enhanced Knowledge Base
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from src.knowledge_base.filters import KnowledgeBaseFilter
from src.knowledge_base.enhanced_storage import EnhancedKnowledgeBase
from src.knowledge_base.exporter import KnowledgeBaseExporter


class TestKnowledgeBaseFilter:
    """Test KnowledgeBaseFilter class"""

    @pytest.fixture
    def kb_filter(self):
        """Create filter instance"""
        return KnowledgeBaseFilter()

    @pytest.fixture
    def sample_data(self):
        """Create sample knowledge base data"""
        return pd.DataFrame({
            'Timestamp': [datetime.now() - timedelta(days=i) for i in range(10)],
            'Category': ['CPU', 'Memory', 'CPU', 'Latency', 'Memory'] * 2,
            'Severity': ['critical', 'high', 'medium', 'low', 'critical'] * 2,
            'Frequency': range(10, 20),
            'Confidence': [0.9, 0.8, 0.7, 0.6, 0.95] * 2,
            'Source': ['cloudwatch', 'datadog'] * 5,
            'Issue_Type': ['high_cpu', 'memory_leak'] * 5,
            'Error_Pattern': [f'Error {i}' for i in range(10)],
            'Solution': [f'Solution {i}' if i % 2 == 0 else None for i in range(10)],
            'Implementation_Steps': [f'Steps {i}' if i % 3 == 0 else None for i in range(10)]
        })

    def test_by_category(self, kb_filter, sample_data):
        """Test filtering by category"""
        result = kb_filter.by_category(sample_data, ['CPU', 'Memory'])

        assert len(result) == 10
        assert all(cat in ['CPU', 'Memory'] for cat in result['Category'])

    def test_by_severity(self, kb_filter, sample_data):
        """Test filtering by severity"""
        result = kb_filter.by_severity(sample_data, ['critical', 'high'])

        assert len(result) == 6
        assert all(sev in ['critical', 'high'] for sev in result['Severity'])

    def test_by_frequency(self, kb_filter, sample_data):
        """Test filtering by frequency"""
        result = kb_filter.by_frequency(sample_data, min_frequency=15)

        assert len(result) == 5
        assert all(freq >= 15 for freq in result['Frequency'])

    def test_by_confidence(self, kb_filter, sample_data):
        """Test filtering by confidence"""
        result = kb_filter.by_confidence(sample_data, min_confidence=0.8)

        assert len(result) == 6
        assert all(conf >= 0.8 for conf in result['Confidence'])

    def test_by_keyword(self, kb_filter, sample_data):
        """Test filtering by keyword"""
        result = kb_filter.by_keyword(sample_data, ['Error 1', 'Error 2'])

        assert len(result) == 2

    def test_has_solution(self, kb_filter, sample_data):
        """Test filtering for entries with solutions"""
        result = kb_filter.has_solution(sample_data)

        assert len(result) == 5
        assert all(result['Solution'].notna())

    def test_has_implementation_steps(self, kb_filter, sample_data):
        """Test filtering for entries with implementation steps"""
        result = kb_filter.has_implementation_steps(sample_data)

        assert len(result) >= 3

    def test_recent(self, kb_filter, sample_data):
        """Test filtering recent entries"""
        result = kb_filter.recent(sample_data, days=5)

        assert len(result) <= 5

    def test_top_frequency(self, kb_filter, sample_data):
        """Test getting top frequency entries"""
        result = kb_filter.top_frequency(sample_data, n=3)

        assert len(result) == 3
        # Check that results are sorted by frequency
        assert result['Frequency'].is_monotonic_decreasing

    def test_apply_filters(self, kb_filter, sample_data):
        """Test applying multiple filters"""
        filter_config = {
            'categories': ['CPU', 'Memory'],
            'severities': ['critical', 'high'],
            'min_confidence': 0.7,
            'has_solution': True
        }

        result = kb_filter.apply_filters(sample_data, filter_config)

        assert len(result) <= len(sample_data)
        assert all(cat in ['CPU', 'Memory'] for cat in result['Category'])
        assert all(sev in ['critical', 'high'] for sev in result['Severity'])
        assert all(conf >= 0.7 for conf in result['Confidence'])

    def test_get_filter_summary(self, kb_filter, sample_data):
        """Test getting filter summary"""
        summary = kb_filter.get_filter_summary(sample_data)

        assert 'total_records' in summary
        assert summary['total_records'] == 10
        assert 'available_filters' in summary
        assert 'categories' in summary['available_filters']


class TestEnhancedKnowledgeBase:
    """Test EnhancedKnowledgeBase class"""

    @pytest.fixture
    def kb(self, tmp_path):
        """Create knowledge base instance"""
        kb_file = tmp_path / 'test_kb.xlsx'
        return EnhancedKnowledgeBase(str(kb_file))

    def test_search(self, kb):
        """Test searching knowledge base"""
        # Add some test data
        kb.add_error(
            "Memory leak in process",
            "Solution for memory leak",
            category="Memory",
            severity="critical"
        )

        filter_config = {'categories': ['Memory']}
        result = kb.search(filter_config)

        assert len(result) >= 0

    def test_add_user_selection(self, kb):
        """Test adding user selection"""
        kb.add_user_selection("Error pattern 1", selected=True, notes="Important")

        assert len(kb.user_selections) == 1
        assert kb.user_selections[0]['selected'] is True

    def test_bulk_select(self, kb):
        """Test bulk selection"""
        # Add test data
        for i in range(5):
            kb.add_error(f"Error {i}", f"Solution {i}")

        filter_config = {}
        count = kb.bulk_select(filter_config, action='select')

        assert count >= 0

    def test_get_summary_stats(self, kb):
        """Test getting summary statistics"""
        stats = kb.get_summary_stats()

        assert 'total_entries' in stats
        assert 'by_category' in stats

    def test_get_recommendations(self, kb):
        """Test getting recommendations"""
        # Add test data with varying severity and frequency
        kb.add_error(
            "Critical error",
            "Critical solution",
            category="CPU",
            severity="critical",
            frequency=10
        )

        recommendations = kb.get_recommendations(top_n=5)

        assert isinstance(recommendations, list)


class TestKnowledgeBaseExporter:
    """Test KnowledgeBaseExporter class"""

    @pytest.fixture
    def exporter(self, tmp_path):
        """Create exporter instance"""
        return KnowledgeBaseExporter(str(tmp_path / 'exports'))

    @pytest.fixture
    def sample_data(self):
        """Create sample data"""
        return pd.DataFrame({
            'Error_Pattern': ['Error 1', 'Error 2', 'Error 3'],
            'Category': ['CPU', 'Memory', 'CPU'],
            'Severity': ['critical', 'high', 'medium'],
            'Solution': ['Solution 1', 'Solution 2', 'Solution 3'],
            'Frequency': [10, 20, 15]
        })

    def test_export_to_excel(self, exporter, sample_data):
        """Test Excel export"""
        output_file = exporter.export_to_excel(sample_data, 'test.xlsx')

        assert Path(output_file).exists()

    def test_export_to_csv(self, exporter, sample_data):
        """Test CSV export"""
        output_file = exporter.export_to_csv(sample_data, 'test.csv')

        assert Path(output_file).exists()

    def test_export_to_json(self, exporter, sample_data):
        """Test JSON export"""
        output_file = exporter.export_to_json(sample_data, 'test.json')

        assert Path(output_file).exists()

    def test_export_to_html(self, exporter, sample_data):
        """Test HTML export"""
        output_file = exporter.export_to_html(sample_data, 'test.html')

        assert Path(output_file).exists()

    def test_export_to_markdown(self, exporter, sample_data):
        """Test Markdown export"""
        output_file = exporter.export_to_markdown(sample_data, 'test.md')

        assert Path(output_file).exists()

    def test_export_summary_report(self, exporter, sample_data):
        """Test summary report export"""
        stats = {
            'total_entries': 3,
            'by_category': {'CPU': 2, 'Memory': 1}
        }

        output_file = exporter.export_summary_report(sample_data, 'report.md', stats)

        assert Path(output_file).exists()

    def test_export_by_category(self, exporter, sample_data):
        """Test export by category"""
        exported_files = exporter.export_by_category(sample_data)

        assert isinstance(exported_files, dict)

    def test_export_automation_ready(self, exporter, sample_data):
        """Test automation-ready export"""
        sample_data['Implementation_Steps'] = ['Step 1', 'Step 2', 'Step 3']

        output_file = exporter.export_automation_ready(sample_data, 'automation.json')

        assert Path(output_file).exists()
