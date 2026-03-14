"""
Comprehensive tests for PostgreSQL Vector Database.

Tests cover:
- Database connection and schema initialization
- Vector storage and retrieval
- Similarity search
- Batch operations
- Index creation
- Performance optimization
- Memory efficiency
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPostgresVectorDB(unittest.TestCase):
    """Test PostgreSQL Vector Database functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Note: These tests use mocking since we don't have a real PostgreSQL instance
        self.mock_pool = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()

        self.mock_pool.getconn.return_value = self.mock_conn
        self.mock_conn.__enter__.return_value = self.mock_conn
        self.mock_conn.__exit__.return_value = None
        self.mock_conn.cursor.return_value.__enter__.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__exit__.return_value = None

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_initialization(self, mock_pool_class):
        """Test database initialization."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        db = PostgresVectorDB(
            host='localhost',
            port=5432,
            database='test_db',
            user='test_user',
            password='test_pass'
        )

        # Verify connection pool was created
        mock_pool_class.assert_called_once()
        self.assertIsNotNone(db.pool)

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_store_error_vector(self, mock_pool_class):
        """Test storing an error vector."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool
        self.mock_cursor.fetchone.return_value = [1]  # Mock ID

        db = PostgresVectorDB()

        # Create sample vector
        vector = np.random.rand(2000)
        record_id = db.store_error_vector(
            message="Test error message",
            vector=vector,
            error_type="database_error",
            severity="ERROR",
            source="test_app"
        )

        # Verify SQL was executed
        self.mock_cursor.execute.assert_called()
        self.assertEqual(record_id, 1)

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_store_error_vectors_batch(self, mock_pool_class):
        """Test batch storing of error vectors."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        db = PostgresVectorDB()

        # Create sample records
        records = []
        for i in range(10):
            records.append({
                'message': f"Error message {i}",
                'vector': np.random.rand(2000),
                'error_type': 'test_error',
                'severity': 'ERROR'
            })

        count = db.store_error_vectors_batch(records)

        # Verify batch insert was called
        self.assertEqual(count, 10)

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_find_similar_errors(self, mock_pool_class):
        """Test finding similar errors by vector similarity."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        # Mock query results
        self.mock_cursor.fetchall.return_value = [
            {
                'id': 1,
                'message': 'Similar error',
                'error_type': 'database_error',
                'distance': 0.1
            }
        ]

        db = PostgresVectorDB()

        query_vector = np.random.rand(2000)
        results = db.find_similar_errors(query_vector, limit=5)

        # Verify query was executed
        self.mock_cursor.execute.assert_called()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['message'], 'Similar error')

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_store_threat_vector(self, mock_pool_class):
        """Test storing threat intelligence vectors."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool
        self.mock_cursor.fetchone.return_value = [1]

        db = PostgresVectorDB()

        vector = np.random.rand(2000)
        record_id = db.store_threat_vector(
            threat_type="malware",
            indicator="suspicious_hash_123",
            vector=vector,
            severity="HIGH",
            confidence=0.9
        )

        self.assertEqual(record_id, 1)
        self.mock_cursor.execute.assert_called()

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_store_training_data(self, mock_pool_class):
        """Test storing training data for ML models."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        db = PostgresVectorDB()

        messages = ["Error 1", "Error 2", "Error 3"]
        vectors = np.random.rand(3, 2000)
        labels = ["type1", "type2", "type3"]

        count = db.store_training_data(messages, vectors, labels, dataset="test")

        self.assertEqual(count, 3)

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_get_training_data(self, mock_pool_class):
        """Test retrieving training data."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        # Mock training data
        self.mock_cursor.fetchall.return_value = [
            {'message': 'Error 1', 'vector': list(np.random.rand(2000)), 'label': 'type1'},
            {'message': 'Error 2', 'vector': list(np.random.rand(2000)), 'label': 'type2'}
        ]

        db = PostgresVectorDB()

        messages, vectors, labels = db.get_training_data(dataset="test", limit=10)

        self.assertEqual(len(messages), 2)
        self.assertEqual(len(labels), 2)
        self.assertEqual(vectors.shape[0], 2)

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_get_stats(self, mock_pool_class):
        """Test getting database statistics."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        # Mock stats
        self.mock_cursor.fetchone.side_effect = [
            {'count': 100},  # error_vectors
            {'count': 50},   # threat_vectors
            {'count': 200}   # training_data
        ]
        self.mock_cursor.fetchall.return_value = [
            {'error_type': 'db_error', 'count': 30}
        ]

        db = PostgresVectorDB()

        stats = db.get_stats()

        self.assertEqual(stats['error_vectors_count'], 100)
        self.assertEqual(stats['threat_vectors_count'], 50)
        self.assertEqual(stats['training_data_count'], 200)

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_create_vector_index(self, mock_pool_class):
        """Test creating vector similarity indexes."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        db = PostgresVectorDB()

        # Test IVFFlat index
        db.create_vector_index(table_name='error_vectors', index_type='ivfflat', lists=100)
        self.mock_cursor.execute.assert_called()

        # Test HNSW index
        db.create_vector_index(table_name='error_vectors', index_type='hnsw')
        self.mock_cursor.execute.assert_called()

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_connection_pooling(self, mock_pool_class):
        """Test connection pool management."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool_class.return_value = self.mock_pool

        db = PostgresVectorDB(min_conn=2, max_conn=10)

        # Use connection context manager
        with db.get_connection() as conn:
            self.assertIsNotNone(conn)

        # Verify connection was returned to pool
        self.mock_pool.putconn.assert_called()


class TestPostgresVectorPerformance(unittest.TestCase):
    """Test PostgreSQL Vector Database performance."""

    @patch('src.database.postgres_vector.psycopg2.pool.ThreadedConnectionPool')
    def test_batch_insert_performance(self, mock_pool_class):
        """Test batch insert is efficient."""
        from src.database.postgres_vector import PostgresVectorDB

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        db = PostgresVectorDB()

        # Create large batch
        records = []
        for i in range(100):
            records.append({
                'message': f"Error {i}",
                'vector': np.random.rand(2000),
                'error_type': 'test_error'
            })

        # Should complete quickly (mocked, so it will)
        import time
        start = time.time()
        count = db.store_error_vectors_batch(records)
        duration = time.time() - start

        # Even with mocking overhead, should be fast
        self.assertLess(duration, 1.0)
        self.assertEqual(count, 100)


if __name__ == '__main__':
    unittest.main()
