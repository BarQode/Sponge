#!/bin/bash
# ================================================================
# Sponge RCA Platform - macOS Setup Script
# ================================================================
#
# This script sets up Sponge RCA on macOS with:
# - PostgreSQL 14+ with pgvector extension
# - Python 3.10+ environment
# - All required dependencies
# - Database initialization
#
# Requirements:
# - macOS 10.15 (Catalina) or later
# - Homebrew package manager
#
# Usage:
#   chmod +x scripts/setup-macos.sh
#   ./scripts/setup-macos.sh
#
# ================================================================

set -e  # Exit on error

echo "============================================================"
echo "Sponge RCA Platform - macOS Setup"
echo "============================================================"

# ================================================================
# 1. Check Homebrew Installation
# ================================================================

echo ""
echo "[1/7] Checking Homebrew installation..."

if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "Homebrew is already installed!"
    brew update
fi

# ================================================================
# 2. Install System Dependencies
# ================================================================

echo ""
echo "[2/7] Installing system dependencies..."

# Install PostgreSQL with pgvector
brew install postgresql@14

# Install pgvector extension
brew tap pgvector/pgvector
brew install pgvector

# Install Python
brew install python@3.10

# Install other dependencies
brew install git wget curl

# ================================================================
# 3. Start PostgreSQL
# ================================================================

echo ""
echo "[3/7] Starting PostgreSQL service..."

# Start PostgreSQL
brew services start postgresql@14

# Wait for PostgreSQL to start
sleep 5

# ================================================================
# 4. Configure PostgreSQL
# ================================================================

echo ""
echo "[4/7] Configuring PostgreSQL database..."

# Create database and user
psql postgres <<EOF
-- Create database
CREATE DATABASE sponge;

-- Create user
CREATE USER sponge WITH PASSWORD 'sponge_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sponge TO sponge;

\q
EOF

# Configure database with pgvector
psql -d sponge <<EOF
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO sponge;

\q
EOF

echo "PostgreSQL database configured successfully!"

# ================================================================
# 5. Create Python Virtual Environment
# ================================================================

echo ""
echo "[5/7] Creating Python virtual environment..."

# Remove existing venv if present
rm -rf venv

# Create new venv with Python 3.10
python3.10 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# ================================================================
# 6. Install Python Dependencies
# ================================================================

echo ""
echo "[6/7] Installing Python dependencies..."

pip install -r requirements.txt

# ================================================================
# 7. Initialize Database Schema
# ================================================================

echo ""
echo "[7/7] Initializing database schema..."

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
echo "Homebrew Services:"
echo "  - PostgreSQL: $(brew services list | grep postgresql@14)"
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
echo "To stop PostgreSQL:"
echo "  brew services stop postgresql@14"
echo ""
echo "============================================================"
