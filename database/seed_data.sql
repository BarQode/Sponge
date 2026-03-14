-- ================================================================
-- Sponge RCA Database Seed Data Script
-- ================================================================
--
-- This script populates the database with sample training data
-- for testing and development purposes.
--
-- Includes:
-- - Sample error messages with vectors
-- - Threat intelligence samples
-- - Training data for KNN model
-- - Model metadata entries
--
-- ================================================================

SET search_path TO sponge, public;

-- ================================================================
-- 1. SAMPLE ERROR VECTORS
-- ================================================================

-- Database Errors
INSERT INTO error_vectors (message, error_type, severity, source, metadata) VALUES
('Database connection failed: Connection refused', 'database_error', 'ERROR', 'webapp', '{"database": "postgres", "port": 5432}'::jsonb),
('Failed to connect to MySQL server at localhost:3306', 'database_error', 'ERROR', 'api', '{"database": "mysql", "port": 3306}'::jsonb),
('Connection timeout to database server', 'database_error', 'ERROR', 'worker', '{"timeout": 30, "database": "mongodb"}'::jsonb),
('Database query timeout after 60 seconds', 'database_error', 'WARNING', 'webapp', '{"query_time": 60}'::jsonb),
('Too many database connections: max 100 reached', 'database_error', 'CRITICAL', 'api', '{"max_connections": 100}'::jsonb);

-- Memory Errors
INSERT INTO error_vectors (message, error_type, severity, source, metadata) VALUES
('Out of memory: Cannot allocate 2GB', 'memory_error', 'CRITICAL', 'worker', '{"requested_memory": "2GB"}'::jsonb),
('Memory allocation failed for buffer', 'memory_error', 'ERROR', 'service', '{"buffer_size": "512MB"}'::jsonb),
('Insufficient memory: Only 100MB available', 'memory_error', 'WARNING', 'webapp', '{"available_memory": "100MB"}'::jsonb),
('Memory leak detected: 500MB over 1 hour', 'memory_error', 'ERROR', 'daemon', '{"leak_rate": "500MB/hour"}'::jsonb),
('Java heap space OutOfMemoryError', 'memory_error', 'CRITICAL', 'java_app', '{"heap_max": "4GB", "heap_used": "4GB"}'::jsonb);

-- Network Errors
INSERT INTO error_vectors (message, error_type, severity, source, metadata) VALUES
('Network unreachable: No route to host', 'network_error', 'ERROR', 'client', '{"target_host": "192.168.1.100"}'::jsonb),
('Connection refused by remote server', 'network_error', 'ERROR', 'api', '{"remote_port": 8080}'::jsonb),
('Timeout connecting to external API', 'network_error', 'WARNING', 'integration', '{"timeout": 30, "api": "stripe"}'::jsonb),
('DNS resolution failed for domain', 'network_error', 'ERROR', 'dns_client', '{"domain": "api.example.com"}'::jsonb),
('Socket timeout after 60 seconds', 'network_error', 'WARNING', 'socket_app', '{"timeout": 60}'::jsonb);

-- Disk Errors
INSERT INTO error_vectors (message, error_type, severity, source, metadata) VALUES
('Disk full: No space left on device', 'disk_error', 'CRITICAL', 'logger', '{"disk": "/dev/sda1", "available": "0MB"}'::jsonb),
('Write failed: Disk quota exceeded', 'disk_error', 'ERROR', 'file_service', '{"quota": "10GB", "used": "10GB"}'::jsonb),
('I/O error reading from disk', 'disk_error', 'ERROR', 'database', '{"disk": "/dev/sdb1"}'::jsonb),
('Disk read timeout after 10 seconds', 'disk_error', 'WARNING', 'storage', '{"timeout": 10}'::jsonb),
('File system is read-only', 'disk_error', 'CRITICAL', 'mount_service', '{"filesystem": "/mnt/data"}'::jsonb);

-- Authentication Errors
INSERT INTO error_vectors (message, error_type, severity, source, metadata) VALUES
('Authentication failed: Invalid credentials', 'auth_error', 'WARNING', 'auth_service', '{"user": "admin", "ip": "192.168.1.50"}'::jsonb),
('Token expired: Please re-authenticate', 'auth_error', 'INFO', 'api', '{"token_age": "7200s"}'::jsonb),
('Unauthorized access attempt detected', 'auth_error', 'ERROR', 'security', '{"ip": "203.0.113.45", "endpoint": "/admin"}'::jsonb),
('Invalid API key provided', 'auth_error', 'WARNING', 'api_gateway', '{"key_prefix": "sk_test_"}'::jsonb),
('Session expired: Please login again', 'auth_error', 'INFO', 'webapp', '{"session_duration": "3600s"}'::jsonb);

-- Application Errors
INSERT INTO error_vectors (message, error_type, severity, source, metadata) VALUES
('Null pointer exception in UserService', 'application_error', 'ERROR', 'java_app', '{"class": "UserService", "line": 145}'::jsonb),
('Undefined variable: user_id in script.js', 'application_error', 'ERROR', 'frontend', '{"file": "script.js", "line": 67}'::jsonb),
('Division by zero in calculation module', 'application_error', 'ERROR', 'calculator', '{"module": "math_utils"}'::jsonb),
('Index out of bounds: list index 10 > length 5', 'application_error', 'ERROR', 'python_app', '{"index": 10, "length": 5}'::jsonb),
('Type error: Cannot convert string to integer', 'application_error', 'ERROR', 'data_processor', '{"value": "abc", "expected_type": "int"}'::jsonb);

-- ================================================================
-- 2. SAMPLE THREAT VECTORS
-- ================================================================

INSERT INTO threat_vectors (threat_type, indicator, severity, confidence, source, metadata) VALUES
('malware', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'HIGH', 0.95, 'virustotal', '{"detection_ratio": "45/67", "file_type": "exe"}'::jsonb),
('phishing', 'http://evil-example.com/login', 'CRITICAL', 0.92, 'url_scanner', '{"domain_age_days": 1, "ssl": false}'::jsonb),
('c2_server', '192.0.2.100', 'CRITICAL', 0.88, 'threat_feed', '{"first_seen": "2024-01-01", "country": "Unknown"}'::jsonb),
('brute_force', '203.0.113.50', 'MEDIUM', 0.75, 'firewall', '{"failed_attempts": 150, "timespan_minutes": 5}'::jsonb),
('suspicious_domain', 'malware-download.xyz', 'HIGH', 0.85, 'dns_monitor', '{"domain_age_days": 3, "registrar": "suspicious"}'::jsonb);

-- ================================================================
-- 3. SAMPLE TRAINING DATA
-- ================================================================

-- Database error patterns
INSERT INTO training_data (message, label, dataset, metadata) VALUES
('Connection to database failed', 'database_error', 'production', '{"version": "1.0"}'::jsonb),
('Database connection timeout', 'database_error', 'production', '{"version": "1.0"}'::jsonb),
('Failed to connect to DB server', 'database_error', 'production', '{"version": "1.0"}'::jsonb),
('Cannot establish database connection', 'database_error', 'production', '{"version": "1.0"}'::jsonb),
('DB connection pool exhausted', 'database_error', 'production', '{"version": "1.0"}'::jsonb);

-- Memory error patterns
INSERT INTO training_data (message, label, dataset, metadata) VALUES
('Out of memory exception', 'memory_error', 'production', '{"version": "1.0"}'::jsonb),
('Cannot allocate memory', 'memory_error', 'production', '{"version": "1.0"}'::jsonb),
('Memory allocation failed', 'memory_error', 'production', '{"version": "1.0"}'::jsonb),
('Insufficient memory available', 'memory_error', 'production', '{"version": "1.0"}'::jsonb),
('Java heap space error', 'memory_error', 'production', '{"version": "1.0"}'::jsonb);

-- Network error patterns
INSERT INTO training_data (message, label, dataset, metadata) VALUES
('Network connection timeout', 'network_error', 'production', '{"version": "1.0"}'::jsonb),
('Connection refused by server', 'network_error', 'production', '{"version": "1.0"}'::jsonb),
('No route to host', 'network_error', 'production', '{"version": "1.0"}'::jsonb),
('Network unreachable', 'network_error', 'production', '{"version": "1.0"}'::jsonb),
('Socket connection failed', 'network_error', 'production', '{"version": "1.0"}'::jsonb);

-- Disk error patterns
INSERT INTO training_data (message, label, dataset, metadata) VALUES
('Disk full error', 'disk_error', 'production', '{"version": "1.0"}'::jsonb),
('No space left on device', 'disk_error', 'production', '{"version": "1.0"}'::jsonb),
('Disk quota exceeded', 'disk_error', 'production', '{"version": "1.0"}'::jsonb),
('I/O error on disk', 'disk_error', 'production', '{"version": "1.0"}'::jsonb),
('File system read-only', 'disk_error', 'production', '{"version": "1.0"}'::jsonb);

-- Auth error patterns
INSERT INTO training_data (message, label, dataset, metadata) VALUES
('Authentication failed', 'auth_error', 'production', '{"version": "1.0"}'::jsonb),
('Invalid credentials', 'auth_error', 'production', '{"version": "1.0"}'::jsonb),
('Access denied', 'auth_error', 'production', '{"version": "1.0"}'::jsonb),
('Unauthorized access', 'auth_error', 'production', '{"version": "1.0"}'::jsonb),
('Token expired', 'auth_error', 'production', '{"version": "1.0"}'::jsonb);

-- ================================================================
-- 4. SAMPLE MODEL METADATA
-- ================================================================

INSERT INTO model_metadata (model_name, model_type, version, accuracy, precision_score, recall_score, f1_score, parameters, training_date, training_samples) VALUES
(
    'knn_error_classifier_v1',
    'knn',
    '1.0.0',
    0.92,
    0.89,
    0.91,
    0.90,
    '{"n_neighbors": 5, "metric": "euclidean", "weights": "distance", "max_features": 2000}'::jsonb,
    NOW() - INTERVAL '7 days',
    500
),
(
    'random_forest_rca_v2',
    'random_forest',
    '2.1.0',
    0.88,
    0.85,
    0.87,
    0.86,
    '{"n_estimators": 100, "max_depth": 20, "min_samples_split": 2}'::jsonb,
    NOW() - INTERVAL '3 days',
    1000
),
(
    'dbscan_clustering_v1',
    'dbscan',
    '1.0.0',
    NULL,
    NULL,
    NULL,
    NULL,
    '{"eps": 0.5, "min_samples": 5}'::jsonb,
    NOW() - INTERVAL '1 day',
    300
);

-- ================================================================
-- 5. SAMPLE RCA SESSIONS
-- ================================================================

INSERT INTO rca_sessions (session_name, status, root_cause, recommended_action, confidence, started_at, completed_at, metadata) VALUES
(
    'Database Connection Issue - 2024-01-15',
    'completed',
    'Database server was unreachable due to firewall rule blocking port 5432',
    'Update firewall rules to allow PostgreSQL traffic from application servers',
    0.95,
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '1 hour',
    '{"analyst": "automated", "tickets": ["SPONGE-123"]}'::jsonb
),
(
    'Memory Leak Investigation - 2024-01-14',
    'completed',
    'Memory leak in caching layer not releasing objects after TTL expiration',
    'Patch caching library to version 2.1.3 or implement manual cleanup',
    0.88,
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '23 hours',
    '{"analyst": "automated", "affected_services": ["cache-service"]}'::jsonb
),
(
    'Network Timeout Analysis - 2024-01-16',
    'in_progress',
    NULL,
    NULL,
    NULL,
    NOW() - INTERVAL '30 minutes',
    NULL,
    '{"analyst": "automated", "target": "api.external.com"}'::jsonb
);

-- ================================================================
-- 6. CREATE VECTOR INDEXES (Optional - for production)
-- ================================================================

-- Function to create vector indexes (call manually when ready)
CREATE OR REPLACE FUNCTION create_vector_indexes()
RETURNS void AS $$
BEGIN
    -- Check if we have enough data for IVFFlat
    IF (SELECT COUNT(*) FROM error_vectors WHERE vector IS NOT NULL) >= 100 THEN
        -- Create IVFFlat index for error vectors
        CREATE INDEX IF NOT EXISTS idx_error_vectors_ivfflat
        ON error_vectors USING ivfflat (vector vector_l2_ops)
        WITH (lists = 100);

        RAISE NOTICE 'Created IVFFlat index on error_vectors';
    ELSE
        RAISE NOTICE 'Not enough data for IVFFlat index on error_vectors (need >= 100 rows)';
    END IF;

    IF (SELECT COUNT(*) FROM threat_vectors WHERE vector IS NOT NULL) >= 100 THEN
        -- Create IVFFlat index for threat vectors
        CREATE INDEX IF NOT EXISTS idx_threat_vectors_ivfflat
        ON threat_vectors USING ivfflat (vector vector_l2_ops)
        WITH (lists = 50);

        RAISE NOTICE 'Created IVFFlat index on threat_vectors';
    ELSE
        RAISE NOTICE 'Not enough data for IVFFlat index on threat_vectors (need >= 100 rows)';
    END IF;

    IF (SELECT COUNT(*) FROM training_data WHERE vector IS NOT NULL) >= 100 THEN
        -- Create IVFFlat index for training data
        CREATE INDEX IF NOT EXISTS idx_training_data_ivfflat
        ON training_data USING ivfflat (vector vector_l2_ops)
        WITH (lists = 50);

        RAISE NOTICE 'Created IVFFlat index on training_data';
    ELSE
        RAISE NOTICE 'Not enough data for IVFFlat index on training_data (need >= 100 rows)';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- 7. DATABASE STATISTICS
-- ================================================================

DO $$
DECLARE
    error_count INTEGER;
    threat_count INTEGER;
    training_count INTEGER;
    model_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO error_count FROM error_vectors;
    SELECT COUNT(*) INTO threat_count FROM threat_vectors;
    SELECT COUNT(*) INTO training_count FROM training_data;
    SELECT COUNT(*) INTO model_count FROM model_metadata;

    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Database Seeding Complete!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Error Vectors: % records', error_count;
    RAISE NOTICE 'Threat Vectors: % records', threat_count;
    RAISE NOTICE 'Training Data: % records', training_count;
    RAISE NOTICE 'Model Metadata: % records', model_count;
    RAISE NOTICE '';
    RAISE NOTICE 'To create vector indexes (when you have more data):';
    RAISE NOTICE '  SELECT create_vector_indexes();';
    RAISE NOTICE '';
    RAISE NOTICE 'To view sample data:';
    RAISE NOTICE '  SELECT * FROM error_vectors LIMIT 5;';
    RAISE NOTICE '  SELECT * FROM recent_errors;';
    RAISE NOTICE '  SELECT * FROM error_stats_by_type;';
    RAISE NOTICE '============================================================';
END $$;
