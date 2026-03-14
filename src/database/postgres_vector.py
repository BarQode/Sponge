"""
PostgreSQL Vector Database for Machine Learning

This module provides comprehensive PostgreSQL vector database support for ML:
- pgvector extension for vector similarity search
- Optimized schema for error/threat vectors
- Efficient indexing strategies (IVFFlat, HNSW)
- Vector similarity queries
- Batch operations
- Connection pooling

Features:
- Store TF-IDF vectors and embeddings
- Fast nearest neighbor search
- Error pattern clustering
- Threat intelligence storage
- Performance-optimized queries
"""

import logging
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import execute_batch, RealDictCursor
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PostgresVectorDB:
    """
    PostgreSQL vector database with pgvector extension support.

    Provides optimized storage and retrieval of ML feature vectors
    for error detection and threat analysis.
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 5432,
        database: str = 'sponge',
        user: str = 'postgres',
        password: str = '',
        min_conn: int = 2,
        max_conn: int = 10
    ):
        """
        Initialize PostgreSQL vector database connection.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Username
            password: Password
            min_conn: Minimum connections in pool
            max_conn: Maximum connections in pool
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user

        try:
            # Create connection pool
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                min_conn,
                max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=10
            )

            logger.info(
                f"Initialized PostgreSQL Vector DB connection pool "
                f"({min_conn}-{max_conn} connections)"
            )

            # Initialize database schema
            self._initialize_schema()

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            Database connection from pool
        """
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        finally:
            if conn:
                self.pool.putconn(conn)

    def _initialize_schema(self):
        """Initialize database schema with vector support."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Enable pgvector extension
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                    # Create error_vectors table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS error_vectors (
                            id SERIAL PRIMARY KEY,
                            message_hash VARCHAR(64) UNIQUE NOT NULL,
                            message TEXT NOT NULL,
                            vector vector(2000),
                            error_type VARCHAR(100),
                            severity VARCHAR(20),
                            source VARCHAR(200),
                            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                            metadata JSONB,
                            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                        );
                    """)

                    # Create threat_vectors table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS threat_vectors (
                            id SERIAL PRIMARY KEY,
                            threat_hash VARCHAR(64) UNIQUE NOT NULL,
                            threat_type VARCHAR(100) NOT NULL,
                            indicator VARCHAR(500),
                            vector vector(2000),
                            severity VARCHAR(20),
                            confidence FLOAT,
                            source VARCHAR(200),
                            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                            metadata JSONB,
                            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                        );
                    """)

                    # Create training_data table for KNN
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS training_data (
                            id SERIAL PRIMARY KEY,
                            message TEXT NOT NULL,
                            vector vector(2000),
                            label VARCHAR(100) NOT NULL,
                            dataset VARCHAR(50),
                            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                            metadata JSONB,
                            created_at TIMESTAMP NOT NULL DEFAULT NOW()
                        );
                    """)

                    # Create model_metadata table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS model_metadata (
                            id SERIAL PRIMARY KEY,
                            model_name VARCHAR(100) UNIQUE NOT NULL,
                            model_type VARCHAR(50),
                            version VARCHAR(20),
                            accuracy FLOAT,
                            parameters JSONB,
                            training_date TIMESTAMP,
                            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                        );
                    """)

                    # Create indexes for performance
                    # B-tree indexes for exact matches
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_error_vectors_hash
                        ON error_vectors(message_hash);
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_error_vectors_type
                        ON error_vectors(error_type);
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_error_vectors_timestamp
                        ON error_vectors(timestamp DESC);
                    """)

                    # GIN index for JSONB metadata
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_error_vectors_metadata
                        ON error_vectors USING GIN(metadata);
                    """)

                    # Vector similarity indexes (IVFFlat for approximate nearest neighbor)
                    # Note: IVFFlat requires data to be present before creating
                    # These will be created on-demand when sufficient data exists

                    # Threat vectors indexes
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_threat_vectors_hash
                        ON threat_vectors(threat_hash);
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_threat_vectors_type
                        ON threat_vectors(threat_type);
                    """)

                    # Training data indexes
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_training_data_label
                        ON training_data(label);
                    """)

                    # Create trigger for updated_at
                    cur.execute("""
                        CREATE OR REPLACE FUNCTION update_updated_at_column()
                        RETURNS TRIGGER AS $$
                        BEGIN
                            NEW.updated_at = NOW();
                            RETURN NEW;
                        END;
                        $$ language 'plpgsql';
                    """)

                    cur.execute("""
                        DROP TRIGGER IF EXISTS update_error_vectors_updated_at
                        ON error_vectors;
                    """)
                    cur.execute("""
                        CREATE TRIGGER update_error_vectors_updated_at
                        BEFORE UPDATE ON error_vectors
                        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    """)

                    conn.commit()
                    logger.info("Database schema initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise

    def store_error_vector(
        self,
        message: str,
        vector: np.ndarray,
        error_type: str,
        severity: str = 'INFO',
        source: str = '',
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store an error vector in the database.

        Args:
            message: Error message
            vector: Feature vector (TF-IDF or embedding)
            error_type: Type of error
            severity: Error severity
            source: Error source
            metadata: Additional metadata

        Returns:
            Record ID
        """
        try:
            import hashlib
            message_hash = hashlib.sha256(message.encode()).hexdigest()

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO error_vectors
                        (message_hash, message, vector, error_type, severity, source, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (message_hash) DO UPDATE
                        SET updated_at = NOW(),
                            error_type = EXCLUDED.error_type,
                            severity = EXCLUDED.severity
                        RETURNING id;
                    """, (
                        message_hash,
                        message,
                        vector.tolist(),
                        error_type,
                        severity,
                        source,
                        psycopg2.extras.Json(metadata or {})
                    ))

                    record_id = cur.fetchone()[0]
                    conn.commit()

                    return record_id

        except Exception as e:
            logger.error(f"Error storing error vector: {e}")
            raise

    def store_error_vectors_batch(
        self,
        records: List[Dict[str, Any]]
    ) -> int:
        """
        Store multiple error vectors in a batch.

        Args:
            records: List of record dictionaries with keys:
                - message: Error message
                - vector: Feature vector
                - error_type: Error type
                - severity: Error severity (optional)
                - source: Error source (optional)
                - metadata: Additional metadata (optional)

        Returns:
            Number of records inserted
        """
        try:
            import hashlib

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Prepare data
                    data = []
                    for record in records:
                        message = record['message']
                        message_hash = hashlib.sha256(message.encode()).hexdigest()

                        data.append((
                            message_hash,
                            message,
                            record['vector'].tolist(),
                            record['error_type'],
                            record.get('severity', 'INFO'),
                            record.get('source', ''),
                            psycopg2.extras.Json(record.get('metadata', {}))
                        ))

                    # Batch insert
                    execute_batch(cur, """
                        INSERT INTO error_vectors
                        (message_hash, message, vector, error_type, severity, source, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (message_hash) DO NOTHING
                    """, data, page_size=100)

                    conn.commit()
                    logger.info(f"Stored {len(data)} error vectors in batch")

                    return len(data)

        except Exception as e:
            logger.error(f"Error storing error vectors batch: {e}")
            raise

    def find_similar_errors(
        self,
        query_vector: np.ndarray,
        limit: int = 10,
        error_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar errors using vector similarity search.

        Args:
            query_vector: Query feature vector
            limit: Maximum number of results
            error_type: Filter by error type (optional)

        Returns:
            List of similar error dictionaries
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Use L2 distance (Euclidean) for similarity
                    # Lower distance = more similar
                    if error_type:
                        cur.execute("""
                            SELECT
                                id,
                                message,
                                error_type,
                                severity,
                                source,
                                timestamp,
                                metadata,
                                vector <-> %s::vector AS distance
                            FROM error_vectors
                            WHERE error_type = %s
                            ORDER BY vector <-> %s::vector
                            LIMIT %s;
                        """, (query_vector.tolist(), error_type, query_vector.tolist(), limit))
                    else:
                        cur.execute("""
                            SELECT
                                id,
                                message,
                                error_type,
                                severity,
                                source,
                                timestamp,
                                metadata,
                                vector <-> %s::vector AS distance
                            FROM error_vectors
                            ORDER BY vector <-> %s::vector
                            LIMIT %s;
                        """, (query_vector.tolist(), query_vector.tolist(), limit))

                    results = cur.fetchall()

                    # Convert to list of dicts
                    return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error finding similar errors: {e}")
            return []

    def store_threat_vector(
        self,
        threat_type: str,
        indicator: str,
        vector: np.ndarray,
        severity: str = 'MEDIUM',
        confidence: float = 0.5,
        source: str = '',
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store a threat vector in the database.

        Args:
            threat_type: Type of threat
            indicator: Threat indicator (IP, domain, hash, etc.)
            vector: Feature vector
            severity: Threat severity
            confidence: Confidence score
            source: Threat source
            metadata: Additional metadata

        Returns:
            Record ID
        """
        try:
            import hashlib
            threat_hash = hashlib.sha256(f"{threat_type}:{indicator}".encode()).hexdigest()

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO threat_vectors
                        (threat_hash, threat_type, indicator, vector, severity, confidence, source, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (threat_hash) DO UPDATE
                        SET updated_at = NOW(),
                            confidence = EXCLUDED.confidence,
                            severity = EXCLUDED.severity
                        RETURNING id;
                    """, (
                        threat_hash,
                        threat_type,
                        indicator,
                        vector.tolist(),
                        severity,
                        confidence,
                        source,
                        psycopg2.extras.Json(metadata or {})
                    ))

                    record_id = cur.fetchone()[0]
                    conn.commit()

                    return record_id

        except Exception as e:
            logger.error(f"Error storing threat vector: {e}")
            raise

    def store_training_data(
        self,
        messages: List[str],
        vectors: np.ndarray,
        labels: List[str],
        dataset: str = 'default'
    ) -> int:
        """
        Store training data for KNN model.

        Args:
            messages: List of training messages
            vectors: Feature vectors matrix
            labels: Training labels
            dataset: Dataset name

        Returns:
            Number of records stored
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    data = [
                        (msg, vec.tolist(), label, dataset)
                        for msg, vec, label in zip(messages, vectors, labels)
                    ]

                    execute_batch(cur, """
                        INSERT INTO training_data (message, vector, label, dataset)
                        VALUES (%s, %s, %s, %s)
                    """, data, page_size=100)

                    conn.commit()
                    logger.info(f"Stored {len(data)} training samples")

                    return len(data)

        except Exception as e:
            logger.error(f"Error storing training data: {e}")
            raise

    def get_training_data(
        self,
        dataset: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[List[str], np.ndarray, List[str]]:
        """
        Retrieve training data from database.

        Args:
            dataset: Filter by dataset name (optional)
            limit: Maximum number of records (optional)

        Returns:
            Tuple of (messages, vectors, labels)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if dataset:
                        cur.execute("""
                            SELECT message, vector, label
                            FROM training_data
                            WHERE dataset = %s
                            ORDER BY created_at DESC
                            LIMIT %s;
                        """, (dataset, limit or 10000))
                    else:
                        cur.execute("""
                            SELECT message, vector, label
                            FROM training_data
                            ORDER BY created_at DESC
                            LIMIT %s;
                        """, (limit or 10000,))

                    results = cur.fetchall()

                    messages = [row['message'] for row in results]
                    vectors = np.array([row['vector'] for row in results])
                    labels = [row['label'] for row in results]

                    return messages, vectors, labels

        except Exception as e:
            logger.error(f"Error retrieving training data: {e}")
            return [], np.array([]), []

    def create_vector_index(
        self,
        table_name: str = 'error_vectors',
        index_type: str = 'ivfflat',
        lists: int = 100
    ):
        """
        Create vector similarity index for faster queries.

        Args:
            table_name: Table to index
            index_type: Index type ('ivfflat' or 'hnsw')
            lists: Number of lists for IVFFlat (affects speed/accuracy tradeoff)
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if index_type == 'ivfflat':
                        cur.execute(f"""
                            CREATE INDEX IF NOT EXISTS {table_name}_vector_idx
                            ON {table_name} USING ivfflat (vector vector_l2_ops)
                            WITH (lists = {lists});
                        """)
                    elif index_type == 'hnsw':
                        cur.execute(f"""
                            CREATE INDEX IF NOT EXISTS {table_name}_vector_idx
                            ON {table_name} USING hnsw (vector vector_l2_ops);
                        """)
                    else:
                        raise ValueError(f"Unknown index type: {index_type}")

                    conn.commit()
                    logger.info(f"Created {index_type} vector index on {table_name}")

        except Exception as e:
            logger.error(f"Error creating vector index: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Statistics dictionary
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    stats = {}

                    # Count records
                    cur.execute("SELECT COUNT(*) as count FROM error_vectors;")
                    stats['error_vectors_count'] = cur.fetchone()['count']

                    cur.execute("SELECT COUNT(*) as count FROM threat_vectors;")
                    stats['threat_vectors_count'] = cur.fetchone()['count']

                    cur.execute("SELECT COUNT(*) as count FROM training_data;")
                    stats['training_data_count'] = cur.fetchone()['count']

                    # Get recent errors by type
                    cur.execute("""
                        SELECT error_type, COUNT(*) as count
                        FROM error_vectors
                        GROUP BY error_type
                        ORDER BY count DESC
                        LIMIT 10;
                    """)
                    stats['error_types'] = [dict(row) for row in cur.fetchall()]

                    return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    def close(self):
        """Close all database connections."""
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")

    def __del__(self):
        """Cleanup on deletion."""
        self.close()
