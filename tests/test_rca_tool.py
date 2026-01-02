"""
Comprehensive test suite for the RCA Tool.
Tests ML Engine, Scraper, and Storage components.
"""

import unittest
import os
import sys
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml_engine import LogRCAEngine
from src.scraper import SolutionScraper
from src.storage import KnowledgeBase


class TestLogRCAEngine(unittest.TestCase):
    """Tests for the ML Engine component."""

    def setUp(self):
        """Set up test fixtures."""
        self.raw_logs = [
            "CRITICAL: Database connection failed at 192.168.1.5",
            "CRITICAL: Database connection failed at 10.0.0.2",
            "ERROR: NullPointerException in AuthModule line 123",
            "ERROR: NullPointerException in AuthModule line 456",
            "INFO: User logged in successfully"
        ]
        self.engine = LogRCAEngine()

    def test_log_cleaning_ip_addresses(self):
        """Ensure IP addresses are masked to find the root pattern."""
        log = "Error at 192.168.1.1 with code 500"
        cleaned = self.engine.clean_log(log)
        self.assertIn("<IP>", cleaned)
        self.assertNotIn("192.168.1.1", cleaned)

    def test_log_cleaning_numbers(self):
        """Ensure numbers are masked."""
        log = "Error code 500 at line 123"
        cleaned = self.engine.clean_log(log)
        self.assertIn("<NUM>", cleaned)
        self.assertNotIn("500", cleaned)
        self.assertNotIn("123", cleaned)

    def test_log_cleaning_hex_values(self):
        """Ensure hexadecimal values are masked."""
        log = "Memory address 0x7f8a3c00 caused error"
        cleaned = self.engine.clean_log(log)
        self.assertIn("<HEX>", cleaned)
        self.assertNotIn("0x7f8a3c00", cleaned)

    def test_log_cleaning_empty_input(self):
        """Test cleaning with empty input."""
        self.assertEqual(self.engine.clean_log(""), "")
        self.assertEqual(self.engine.clean_log(None), "")

    def test_vectorization_shape(self):
        """Ensure TensorFlow model produces embeddings of correct shape."""
        cleaned_logs = [self.engine.clean_log(log) for log in self.raw_logs]
        embeddings = self.engine.vectorize(cleaned_logs)

        # Check if output is numpy array
        self.assertIsInstance(embeddings, np.ndarray)
        self.assertEqual(len(embeddings), 5)

    def test_vectorization_empty_input(self):
        """Test vectorization with empty input."""
        embeddings = self.engine.vectorize([])
        self.assertEqual(len(embeddings), 0)

    def test_clustering_basic(self):
        """Test basic clustering functionality."""
        root_causes = self.engine.analyze_root_causes(self.raw_logs)

        # Should identify at least one error pattern
        self.assertIsInstance(root_causes, list)

        if root_causes:
            # Check structure of results
            for rc in root_causes:
                self.assertIn('pattern_id', rc)
                self.assertIn('count', rc)
                self.assertIn('representative_log', rc)
                self.assertIn('original_log_example', rc)

    def test_clustering_with_few_samples(self):
        """Test clustering with too few samples."""
        logs = ["ERROR: Test error 1", "ERROR: Test error 2"]
        root_causes = self.engine.analyze_root_causes(logs)

        # Should handle gracefully
        self.assertIsInstance(root_causes, list)

    def test_get_cluster_statistics(self):
        """Test statistics generation."""
        stats = self.engine.get_cluster_statistics(self.raw_logs)

        self.assertIn('total_logs', stats)
        self.assertEqual(stats['total_logs'], 5)


class TestSolutionScraper(unittest.TestCase):
    """Tests for the Web Scraper component."""

    def setUp(self):
        """Set up test fixtures."""
        self.scraper = SolutionScraper()

    @patch('src.scraper.DDGS')
    def test_scraper_with_results(self, mock_ddgs):
        """Test web scraping with mocked successful results."""
        # Setup mock
        mock_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {
                'body': 'Restart the service to fix NullPointerException.',
                'href': 'https://stackoverflow.com/questions/123'
            }
        ]

        result = self.scraper.find_solution("NullPointerException")

        self.assertIn("solution", result)
        self.assertIn("source", result)
        self.assertIn("confidence", result)
        self.assertIn("Restart", result['solution'])
        self.assertIn("stackoverflow.com", result['source'])

    @patch('src.scraper.DDGS')
    def test_scraper_no_results(self, mock_ddgs):
        """Test scraper when no results are found."""
        mock_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_instance
        mock_instance.text.return_value = []

        result = self.scraper.find_solution("SomeUnknownError")

        self.assertIn("solution", result)
        self.assertIn("No specific solution", result['solution'])

    def test_scraper_empty_input(self):
        """Test scraper with empty input."""
        result = self.scraper.find_solution("")

        self.assertIn("solution", result)
        self.assertEqual(result['confidence'], 'low')

    def test_query_building(self):
        """Test search query construction."""
        query = self.scraper._build_query("ERROR: Database connection failed")

        self.assertIn("solution", query)
        self.assertIn("stackoverflow", query)

    def test_result_scoring(self):
        """Test result scoring mechanism."""
        result_stackoverflow = {
            'href': 'https://stackoverflow.com/questions/123',
            'body': 'This is the solution to fix the error'
        }

        result_generic = {
            'href': 'https://example.com/page',
            'body': 'Some random content'
        }

        score_so = self.scraper._score_result(result_stackoverflow)
        score_generic = self.scraper._score_result(result_generic)

        # StackOverflow should score higher
        self.assertGreater(score_so, score_generic)


class TestKnowledgeBase(unittest.TestCase):
    """Tests for the Knowledge Base storage component."""

    def setUp(self):
        """Set up test fixtures."""
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(
            suffix='.xlsx',
            delete=False
        )
        self.temp_file.close()
        self.kb = KnowledgeBase(filename=self.temp_file.name)

    def tearDown(self):
        """Clean up test files."""
        try:
            os.remove(self.temp_file.name)
        except:
            pass

    def test_initialization(self):
        """Test knowledge base initialization."""
        # File should exist
        self.assertTrue(Path(self.temp_file.name).exists())

        # Should have correct columns
        df = pd.read_excel(self.temp_file.name, engine='openpyxl')
        expected_columns = [
            'Timestamp', 'Error_Pattern', 'Frequency',
            'Solution', 'Source', 'Confidence', 'Last_Updated'
        ]

        for col in expected_columns:
            self.assertIn(col, df.columns)

    def test_save_entry(self):
        """Test saving an entry to the knowledge base."""
        success = self.kb.save_entry(
            error="Test Error Pattern",
            fix="Test Solution",
            source="https://example.com",
            count=5,
            confidence="high"
        )

        self.assertTrue(success)

        # Verify it was saved
        df = pd.read_excel(self.temp_file.name, engine='openpyxl')
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Error_Pattern'], "Test Error Pattern")
        self.assertEqual(df.iloc[0]['Frequency'], 5)

    def test_save_duplicate_entry(self):
        """Test updating an existing entry."""
        # Save first time
        self.kb.save_entry("Error A", "Fix A", "Source A", count=3)

        # Save again (should update)
        self.kb.save_entry("Error A", "Fix A Updated", "Source A", count=2)

        df = pd.read_excel(self.temp_file.name, engine='openpyxl')

        # Should still have only 1 entry
        self.assertEqual(len(df), 1)

        # Frequency should be updated (3 + 2 = 5)
        self.assertEqual(df.iloc[0]['Frequency'], 5)

    def test_check_cache_hit(self):
        """Test cache lookup with existing entry."""
        self.kb.save_entry("Known Error", "Known Solution", "Source", count=1)

        result = self.kb.check_cache("Known Error")

        self.assertIsNotNone(result)
        self.assertEqual(result['solution'], "Known Solution")

    def test_check_cache_miss(self):
        """Test cache lookup with non-existing entry."""
        result = self.kb.check_cache("Unknown Error")
        self.assertIsNone(result)

    def test_get_top_errors(self):
        """Test retrieving top errors."""
        self.kb.save_entry("Error A", "Fix A", "Source A", count=10)
        self.kb.save_entry("Error B", "Fix B", "Source B", count=5)
        self.kb.save_entry("Error C", "Fix C", "Source C", count=15)

        top_errors = self.kb.get_top_errors(limit=2)

        self.assertEqual(len(top_errors), 2)
        # Should be sorted by frequency
        self.assertEqual(top_errors[0]['frequency'], 15)
        self.assertEqual(top_errors[1]['frequency'], 10)

    def test_get_statistics(self):
        """Test statistics generation."""
        self.kb.save_entry("Error A", "Fix A", "Source A", count=10, confidence="high")
        self.kb.save_entry("Error B", "Fix B", "Source B", count=5, confidence="medium")

        stats = self.kb.get_statistics()

        self.assertEqual(stats['total_patterns'], 2)
        self.assertEqual(stats['total_occurrences'], 15)
        self.assertEqual(stats['high_confidence_count'], 1)
        self.assertEqual(stats['medium_confidence_count'], 1)

    def test_export_to_csv(self):
        """Test CSV export functionality."""
        self.kb.save_entry("Error A", "Fix A", "Source A")

        csv_file = tempfile.NamedTemporaryFile(
            suffix='.csv',
            delete=False
        )
        csv_file.close()

        try:
            success = self.kb.export_to_csv(csv_file.name)
            self.assertTrue(success)
            self.assertTrue(Path(csv_file.name).exists())

            # Verify CSV content
            df = pd.read_csv(csv_file.name)
            self.assertEqual(len(df), 1)
        finally:
            os.remove(csv_file.name)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(
            suffix='.xlsx',
            delete=False
        )
        self.temp_file.close()

    def tearDown(self):
        """Clean up."""
        try:
            os.remove(self.temp_file.name)
        except:
            pass

    @patch('src.scraper.DDGS')
    def test_complete_workflow(self, mock_ddgs):
        """Test the complete RCA workflow."""
        # Mock scraper
        mock_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_instance
        mock_instance.text.return_value = [
            {
                'body': 'Solution for database error',
                'href': 'https://stackoverflow.com/q/123'
            }
        ]

        # Initialize components
        engine = LogRCAEngine()
        scraper = SolutionScraper()
        kb = KnowledgeBase(filename=self.temp_file.name)

        # Test logs
        logs = [
            "ERROR: Database connection failed at 192.168.1.1",
            "ERROR: Database connection failed at 10.0.0.5",
            "ERROR: Database connection failed at 172.16.0.1"
        ]

        # Analyze
        root_causes = engine.analyze_root_causes(logs)
        self.assertGreater(len(root_causes), 0)

        # Get solution
        error_pattern = root_causes[0]['representative_log']
        solution = scraper.find_solution(error_pattern)

        # Save to KB
        kb.save_entry(
            error_pattern,
            solution['solution'],
            solution['source'],
            root_causes[0]['count'],
            solution.get('confidence', 'medium')
        )

        # Verify saved
        cached = kb.check_cache(error_pattern)
        self.assertIsNotNone(cached)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
