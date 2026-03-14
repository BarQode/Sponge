#!/bin/bash
# ================================================================
# Sponge RCA Platform - Linux Setup Script
# ================================================================
#
# This script sets up Sponge RCA on Linux systems with:
# - PostgreSQL 14+ with pgvector extension
# - Python 3.9+ environment
# - All required dependencies
# - Database initialization
#
# Supported distributions:
# - Ubuntu 20.04+
# - Debian 11+
# - CentOS 8+
# - Fedora 35+
#
# Usage:
#   chmod +x scripts/setup-linux.sh
#   ./scripts/setup-linux.sh
#
# ================================================================

set -e  # Exit on error

echo "============================================================"
echo "Sponge RCA Platform - Linux Setup"
echo "============================================================"

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo "Error: Cannot detect Linux distribution"
    exit 1
fi

echo "Detected OS: $OS $VER"

# ================================================================
# 1. Install System Dependencies
# ================================================================

echo ""
echo "[1/7] Installing system dependencies..."

if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo apt-get update
    sudo apt-get install -y \
        python3.10 \
        python3.10-venv \
        python3-pip \
        postgresql-14 \
        postgresql-contrib \
        postgresql-14-pgvector \
        build-essential \
        libpq-dev \
        git \
        curl \
        wget

elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "fedora" ]; then
    sudo dnf install -y \
        python310 \
        python3-pip \
        postgresql14-server \
        postgresql14-contrib \
        postgresql14-devel \
        gcc \
        git \
        curl \
        wget

    # Initialize PostgreSQL
    sudo postgresql-setup --initdb

    # Install pgvector from source
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git /tmp/pgvector
    cd /tmp/pgvector
    make
    sudo make install
    cd -
else
    echo "Warning: Unsupported distribution. Please install dependencies manually."
fi

# ================================================================
# 2. Start PostgreSQL
# ================================================================

echo ""
echo "[2/7] Starting PostgreSQL service..."

if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "fedora" ]; then
    sudo systemctl enable postgresql-14
    sudo systemctl start postgresql-14
fi

sleep 3

# ================================================================
# 3. Configure PostgreSQL
# ================================================================

echo ""
echo "[3/7] Configuring PostgreSQL database..."

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
# 4. Create Python Virtual Environment
# ================================================================

echo ""
echo "[4/7] Creating Python virtual environment..."

# Remove existing venv if present
rm -rf venv

# Create new venv
python3.10 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# ================================================================
# 5. Install Python Dependencies
# ================================================================

echo ""
echo "[5/7] Installing Python dependencies..."

pip install -r requirements.txt

# ================================================================
# 6. Initialize Database Schema
# ================================================================

echo ""
echo "[6/7] Initializing database schema..."

# Run init script
PGPASSWORD=sponge_secure_password psql -h localhost -U sponge -d sponge -f database/init_db.sql

# Run seed data
PGPASSWORD=sponge_secure_password psql -h localhost -U sponge -d sponge -f database/seed_data.sql

# ================================================================
# 7. Create Configuration File
# ================================================================

echo ""
echo "[7/7] Creating configuration file..."

# Copy .env.example if .env doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
    echo "Please edit .env and configure your settings!"
else
    echo ".env file already exists, skipping..."
fi

# ================================================================
# Setup Complete
# ================================================================

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
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
echo "Next Steps:"
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Edit configuration:"
echo "     nano .env"
echo ""
echo "  3. Run Sponge RCA:"
echo "     python sponge_app.py --mode cli"
echo ""
echo "  4. Or run with Docker:"
echo "     docker-compose up -d"
echo ""
echo "============================================================"
