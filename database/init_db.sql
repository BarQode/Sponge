-- ================================================================
-- PostgreSQL Database Initialization Script for Sponge RCA
-- ================================================================
--
-- This script initializes the complete database schema with:
-- - pgvector extension for ML vector storage
-- - Tables for error vectors, threats, training data
-- - Optimized indexes for performance
-- - Triggers and constraints
-- - Sample seed data for testing
--
-- Compatible with PostgreSQL 12+ with pgvector extension
-- ================================================================

-- ================================================================
-- 1. EXTENSION SETUP
-- ================================================================

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable advanced text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ================================================================
-- 2. SCHEMA CREATION
-- ================================================================

-- Create dedicated schema for Sponge
CREATE SCHEMA IF NOT EXISTS sponge;

-- Set search path
SET search_path TO sponge, public;

-- ================================================================
-- 3. TABLES
-- ================================================================

-- Error Vectors Table
-- Stores TF-IDF/embedding vectors for error messages
CREATE TABLE IF NOT EXISTS error_vectors (
    id SERIAL PRIMARY KEY,
    message_hash VARCHAR(64) UNIQUE NOT NULL,
    message TEXT NOT NULL,
    vector vector(2000),  -- 2000-dimensional vector for TF-IDF
    error_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
    source VARCHAR(200),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_severity CHECK (severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    CONSTRAINT valid_message CHECK (LENGTH(message) > 0),
    CONSTRAINT valid_error_type CHECK (LENGTH(error_type) > 0)
);

-- Threat Vectors Table
-- Stores threat intelligence vectors
CREATE TABLE IF NOT EXISTS threat_vectors (
    id SERIAL PRIMARY KEY,
    threat_hash VARCHAR(64) UNIQUE NOT NULL,
    threat_type VARCHAR(100) NOT NULL,
    indicator VARCHAR(500) NOT NULL,
    vector vector(2000),
    severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    confidence FLOAT NOT NULL DEFAULT 0.5,
    source VARCHAR(200),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_threat_severity CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT valid_threat_type CHECK (LENGTH(threat_type) > 0),
    CONSTRAINT valid_indicator CHECK (LENGTH(indicator) > 0)
);

-- Training Data Table
-- Stores labeled training data for ML models
CREATE TABLE IF NOT EXISTS training_data (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    vector vector(2000),
    label VARCHAR(100) NOT NULL,
    dataset VARCHAR(50) NOT NULL DEFAULT 'default',
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_training_message CHECK (LENGTH(message) > 0),
    CONSTRAINT valid_label CHECK (LENGTH(label) > 0)
);

-- Model Metadata Table
-- Tracks ML model versions and performance
CREATE TABLE IF NOT EXISTS model_metadata (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) UNIQUE NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    accuracy FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,
    parameters JSONB DEFAULT '{}',
    training_date TIMESTAMP,
    training_samples INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_model_name CHECK (LENGTH(model_name) > 0),
    CONSTRAINT valid_accuracy CHECK (accuracy IS NULL OR (accuracy >= 0.0 AND accuracy <= 1.0)),
    CONSTRAINT valid_precision CHECK (precision_score IS NULL OR (precision_score >= 0.0 AND precision_score <= 1.0)),
    CONSTRAINT valid_recall CHECK (recall_score IS NULL OR (recall_score >= 0.0 AND recall_score <= 1.0))
);

-- Error Clusters Table
-- Stores error clustering results from DBSCAN/KNN
CREATE TABLE IF NOT EXISTS error_clusters (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    error_vector_id INTEGER REFERENCES error_vectors(id) ON DELETE CASCADE,
    distance_to_centroid FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_distance CHECK (distance_to_centroid >= 0.0)
);

-- RCA Sessions Table
-- Tracks root cause analysis sessions
CREATE TABLE IF NOT EXISTS rca_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_name VARCHAR(200),
    error_vector_id INTEGER REFERENCES error_vectors(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    root_cause TEXT,
    recommended_action TEXT,
    confidence FLOAT,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',

    -- Constraints
    CONSTRAINT valid_status CHECK (status IN ('in_progress', 'completed', 'failed', 'cancelled'))
);

-- ================================================================
-- 4. INDEXES
-- ================================================================

-- Error Vectors Indexes
CREATE INDEX IF NOT EXISTS idx_error_vectors_hash ON error_vectors(message_hash);
CREATE INDEX IF NOT EXISTS idx_error_vectors_type ON error_vectors(error_type);
CREATE INDEX IF NOT EXISTS idx_error_vectors_severity ON error_vectors(severity);
CREATE INDEX IF NOT EXISTS idx_error_vectors_timestamp ON error_vectors(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_vectors_created ON error_vectors(created_at DESC);

-- JSONB GIN index for metadata queries
CREATE INDEX IF NOT EXISTS idx_error_vectors_metadata ON error_vectors USING GIN(metadata);

-- Full-text search on messages
CREATE INDEX IF NOT EXISTS idx_error_vectors_message_trgm ON error_vectors USING GIN(message gin_trgm_ops);

-- Threat Vectors Indexes
CREATE INDEX IF NOT EXISTS idx_threat_vectors_hash ON threat_vectors(threat_hash);
CREATE INDEX IF NOT EXISTS idx_threat_vectors_type ON threat_vectors(threat_type);
CREATE INDEX IF NOT EXISTS idx_threat_vectors_severity ON threat_vectors(severity);
CREATE INDEX IF NOT EXISTS idx_threat_vectors_timestamp ON threat_vectors(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_threat_vectors_metadata ON threat_vectors USING GIN(metadata);

-- Training Data Indexes
CREATE INDEX IF NOT EXISTS idx_training_data_label ON training_data(label);
CREATE INDEX IF NOT EXISTS idx_training_data_dataset ON training_data(dataset);
CREATE INDEX IF NOT EXISTS idx_training_data_created ON training_data(created_at DESC);

-- Model Metadata Indexes
CREATE INDEX IF NOT EXISTS idx_model_metadata_name ON model_metadata(model_name);
CREATE INDEX IF NOT EXISTS idx_model_metadata_type ON model_metadata(model_type);
CREATE INDEX IF NOT EXISTS idx_model_metadata_training_date ON model_metadata(training_date DESC);

-- Error Clusters Indexes
CREATE INDEX IF NOT EXISTS idx_error_clusters_cluster_id ON error_clusters(cluster_id);
CREATE INDEX IF NOT EXISTS idx_error_clusters_vector_id ON error_clusters(error_vector_id);

-- RCA Sessions Indexes
CREATE INDEX IF NOT EXISTS idx_rca_sessions_status ON rca_sessions(status);
CREATE INDEX IF NOT EXISTS idx_rca_sessions_started ON rca_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_rca_sessions_metadata ON rca_sessions USING GIN(metadata);

-- ================================================================
-- 5. FUNCTIONS AND TRIGGERS
-- ================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_error_vectors_updated_at ON error_vectors;
CREATE TRIGGER update_error_vectors_updated_at
    BEFORE UPDATE ON error_vectors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_threat_vectors_updated_at ON threat_vectors;
CREATE TRIGGER update_threat_vectors_updated_at
    BEFORE UPDATE ON threat_vectors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_model_metadata_updated_at ON model_metadata;
CREATE TRIGGER update_model_metadata_updated_at
    BEFORE UPDATE ON model_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically hash messages
CREATE OR REPLACE FUNCTION generate_message_hash()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.message_hash IS NULL OR NEW.message_hash = '' THEN
        NEW.message_hash = encode(digest(NEW.message, 'sha256'), 'hex');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic message hashing
DROP TRIGGER IF EXISTS auto_hash_error_message ON error_vectors;
CREATE TRIGGER auto_hash_error_message
    BEFORE INSERT OR UPDATE ON error_vectors
    FOR EACH ROW
    EXECUTE FUNCTION generate_message_hash();

-- ================================================================
-- 6. VIEWS
-- ================================================================

-- View for recent errors
CREATE OR REPLACE VIEW recent_errors AS
SELECT
    ev.id,
    ev.message,
    ev.error_type,
    ev.severity,
    ev.source,
    ev.timestamp,
    ev.metadata,
    COUNT(ec.id) as cluster_count
FROM error_vectors ev
LEFT JOIN error_clusters ec ON ev.id = ec.error_vector_id
WHERE ev.timestamp > NOW() - INTERVAL '24 hours'
GROUP BY ev.id, ev.message, ev.error_type, ev.severity, ev.source, ev.timestamp, ev.metadata
ORDER BY ev.timestamp DESC;

-- View for error statistics by type
CREATE OR REPLACE VIEW error_stats_by_type AS
SELECT
    error_type,
    severity,
    COUNT(*) as total_count,
    COUNT(DISTINCT DATE(timestamp)) as days_active,
    MIN(timestamp) as first_occurrence,
    MAX(timestamp) as last_occurrence,
    AVG(CASE
        WHEN severity = 'CRITICAL' THEN 5
        WHEN severity = 'ERROR' THEN 4
        WHEN severity = 'WARNING' THEN 3
        WHEN severity = 'INFO' THEN 2
        ELSE 1
    END) as avg_severity_score
FROM error_vectors
GROUP BY error_type, severity
ORDER BY total_count DESC;

-- View for model performance
CREATE OR REPLACE VIEW model_performance AS
SELECT
    model_name,
    model_type,
    version,
    accuracy,
    precision_score,
    recall_score,
    f1_score,
    training_samples,
    training_date,
    EXTRACT(EPOCH FROM (NOW() - training_date))/86400 as days_since_training
FROM model_metadata
ORDER BY training_date DESC;

-- ================================================================
-- 7. GRANT PERMISSIONS (for application user)
-- ================================================================

-- Note: Replace 'sponge_app' with your actual application user
-- CREATE USER sponge_app WITH PASSWORD 'secure_password_here';

-- Grant schema usage
-- GRANT USAGE ON SCHEMA sponge TO sponge_app;

-- Grant table permissions
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA sponge TO sponge_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA sponge TO sponge_app;

-- Grant execute on functions
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA sponge TO sponge_app;

-- ================================================================
-- 8. COMPLETION MESSAGE
-- ================================================================

DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Sponge RCA Database Schema Initialized Successfully!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Tables created: 6 (error_vectors, threat_vectors, training_data, model_metadata, error_clusters, rca_sessions)';
    RAISE NOTICE 'Indexes created: 20+';
    RAISE NOTICE 'Views created: 3';
    RAISE NOTICE 'Triggers created: 4';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run seed_data.sql to populate with sample data';
    RAISE NOTICE '2. Create vector indexes: SELECT create_vector_indexes();';
    RAISE NOTICE '3. Configure application connection in config.yml';
    RAISE NOTICE '============================================================';
END $$;
