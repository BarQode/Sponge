#!/bin/bash
# ================================================================
# Sponge RCA Platform - Raspberry Pi Setup Script
# ================================================================
#
# This script sets up Sponge RCA on Raspberry Pi with:
# - PostgreSQL 14+ with pgvector extension
# - Python 3.9+ environment (optimized for ARM)
# - Lightweight dependencies for ARM64/ARMv7
# - Database initialization
#
# Supported:
# - Raspberry Pi 3B+ (ARMv7)
# - Raspberry Pi 4 (ARM64)
# - Raspberry Pi 5 (ARM64)
# - Raspberry Pi OS (Bullseye or later)
#
# Usage:
#   chmod +x scripts/setup-raspberry-pi.sh
#   ./scripts/setup-raspberry-pi.sh
#
# ================================================================

set -e  # Exit on error

echo "============================================================"
echo "Sponge RCA Platform - Raspberry Pi Setup"
echo "============================================================"

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

if [ "$ARCH" != "armv7l" ] && [ "$ARCH" != "aarch64" ]; then
    echo "Warning: This script is optimized for Raspberry Pi (ARM)"
    echo "Detected architecture: $ARCH"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ================================================================
# 1. Update System
# ================================================================

echo ""
echo "[1/8] Updating system packages..."

sudo apt-get update
sudo apt-get upgrade -y

# ================================================================
# 2. Install System Dependencies
# ================================================================

echo ""
echo "[2/8] Installing system dependencies..."

sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    postgresql \
    postgresql-contrib \
    postgresql-server-dev-all \
    build-essential \
    libpq-dev \
    git \
    curl \
    wget \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    gfortran

# ================================================================
# 3. Install pgvector Extension
# ================================================================

echo ""
echo "[3/8] Building and installing pgvector extension..."

# Clone pgvector
cd /tmp
rm -rf pgvector
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector

# Build and install
make
sudo make install

# Return to original directory
cd -

echo "pgvector extension installed!"

# ================================================================
# 4. Start PostgreSQL
# ================================================================

echo ""
echo "[4/8] Starting PostgreSQL service..."

sudo systemctl enable postgresql
sudo systemctl start postgresql

sleep 3

# ================================================================
# 5. Configure PostgreSQL
# ================================================================

echo ""
echo "[5/8] Configuring PostgreSQL database..."

# Create database and user
sudo -u postgres psql <<EOF
-- Create database
CREATE DATABASE sponge;

-- Create user
CREATE USER sponge WITH PASSWORD 'sponge_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sponge TO sponge;

-- Connect to sponge database
\c sponge

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO sponge;

\q
EOF

echo "PostgreSQL database configured successfully!"

# ================================================================
# 6. Create Python Virtual Environment
# ================================================================

echo ""
echo "[6/8] Creating Python virtual environment..."

# Remove existing venv if present
rm -rf venv

# Create new venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# ================================================================
# 7. Install Python Dependencies (ARM-optimized)
# ================================================================

echo ""
echo "[7/8] Installing Python dependencies (ARM-optimized)..."

# Install numpy first (precompiled for ARM)
pip install numpy --only-binary :all:

# Install scipy with OpenBLAS
pip install scipy --only-binary :all:

# Install scikit-learn (may take 10-15 minutes on RPi 3)
echo "Installing scikit-learn (this may take 10-15 minutes on older RPi models)..."
pip install scikit-learn --only-binary :all: || pip install scikit-learn

# Install TensorFlow Lite (lightweight for ARM)
pip install tflite-runtime || pip install tensorflow

# Install remaining dependencies
pip install -r requirements.txt --no-cache-dir

# ================================================================
# 8. Initialize Database Schema
# ================================================================

echo ""
echo "[8/8] Initializing database schema..."

# Run init script
PGPASSWORD=sponge_secure_password psql -h localhost -U sponge -d sponge -f database/init_db.sql

# Run seed data
PGPASSWORD=sponge_secure_password psql -h localhost -U sponge -d sponge -f database/seed_data.sql

# ================================================================
# Create Configuration File
# ================================================================

echo ""
echo "Creating configuration file..."

# Copy .env.example if .env doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
    echo "Please edit .env and configure your settings!"
else
    echo ".env file already exists, skipping..."
fi

# ================================================================
# Performance Tuning for Raspberry Pi
# ================================================================

echo ""
echo "Applying Raspberry Pi performance optimizations..."

# Create optimized config for PostgreSQL on RPi
sudo tee -a /etc/postgresql/*/main/conf.d/raspberry_pi.conf > /dev/null <<EOF
# Raspberry Pi Optimizations
shared_buffers = 128MB
effective_cache_size = 512MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 4
effective_io_concurrency = 2
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 2
max_parallel_workers_per_gather = 1
max_parallel_workers = 2
EOF

# Restart PostgreSQL to apply changes
sudo systemctl restart postgresql

echo "PostgreSQL optimized for Raspberry Pi!"

# ================================================================
# Setup Complete
# ================================================================

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "Raspberry Pi Information:"
echo "  - Model: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
echo "  - Architecture: $ARCH"
echo "  - Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo ""
echo "PostgreSQL Database:"
echo "  - Host: localhost"
echo "  - Port: 5432"
echo "  - Database: sponge"
echo "  - User: sponge"
echo "  - Password: sponge_secure_password"
echo ""
echo "Python Environment:"
echo "  - Virtual environment: venv/"
echo "  - Python version: $(python --version)"
echo ""
echo "Performance Notes:"
echo "  - PostgreSQL has been optimized for Raspberry Pi"
echo "  - ML operations may be slower than x86_64 systems"
echo "  - Consider using lighter models on RPi 3"
echo ""
echo "Next Steps:"
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Edit configuration:"
echo "     nano .env"
echo ""
echo "  3. Run Sponge RCA (lightweight mode):"
echo "     python sponge_app.py --mode cli"
echo ""
echo "  4. Or run with Docker (recommended for RPi 4+):"
echo "     docker-compose up -d"
echo ""
echo "Raspberry Pi Tips:"
echo "  - Use 'htop' to monitor resource usage"
echo "  - Consider external SSD for better I/O performance"
echo "  - Ensure adequate cooling for sustained workloads"
echo ""
echo "============================================================"
