# ================================================================
# Sponge RCA Platform - Windows Setup Script
# ================================================================
#
# This script sets up Sponge RCA on Windows with:
# - PostgreSQL 14+ with pgvector extension
# - Python 3.10+ environment
# - All required dependencies
# - Database initialization
#
# Requirements:
# - Windows 10/11 or Windows Server 2019+
# - PowerShell 5.1 or later
# - Administrator privileges
#
# Usage:
#   Right-click PowerShell and "Run as Administrator"
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\scripts\setup-windows.ps1
#
# ================================================================

# Require Administrator
#Requires -RunAsAdministrator

Write-Host "============================================================"
Write-Host "Sponge RCA Platform - Windows Setup"
Write-Host "============================================================"

# ================================================================
# 1. Check Chocolatey Installation
# ================================================================

Write-Host ""
Write-Host "[1/8] Checking Chocolatey package manager..."

if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Chocolatey not found. Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
} else {
    Write-Host "Chocolatey is already installed!"
    choco upgrade chocolatey -y
}

# ================================================================
# 2. Install System Dependencies
# ================================================================

Write-Host ""
Write-Host "[2/8] Installing system dependencies..."

# Install PostgreSQL
choco install postgresql14 -y --params '/Password:sponge_secure_password'

# Install Python
choco install python310 -y

# Install Git
choco install git -y

# Install Visual C++ Build Tools (required for some Python packages)
choco install visualstudio2022buildtools -y
choco install visualstudio2022-workload-vctools -y

# Refresh environment variables
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# ================================================================
# 3. Install pgvector Extension
# ================================================================

Write-Host ""
Write-Host "[3/8] Installing pgvector extension..."

# Download and install pgvector
$pgvectorUrl = "https://github.com/pgvector/pgvector/releases/download/v0.5.1/pgvector-0.5.1-windows-x64-postgresql14.zip"
$pgvectorZip = "$env:TEMP\pgvector.zip"
$pgvectorExtract = "$env:TEMP\pgvector"

Invoke-WebRequest -Uri $pgvectorUrl -OutFile $pgvectorZip
Expand-Archive -Path $pgvectorZip -DestinationPath $pgvectorExtract -Force

# Copy pgvector files to PostgreSQL directory
$pgDir = "C:\Program Files\PostgreSQL\14"
Copy-Item "$pgvectorExtract\lib\vector.dll" "$pgDir\lib\" -Force
Copy-Item "$pgvectorExtract\share\extension\vector*" "$pgDir\share\extension\" -Force

Write-Host "pgvector extension installed!"

# ================================================================
# 4. Start PostgreSQL Service
# ================================================================

Write-Host ""
Write-Host "[4/8] Starting PostgreSQL service..."

Start-Service postgresql-x64-14
Set-Service postgresql-x64-14 -StartupType Automatic

Start-Sleep -Seconds 5

# ================================================================
# 5. Configure PostgreSQL
# ================================================================

Write-Host ""
Write-Host "[5/8] Configuring PostgreSQL database..."

# Set PostgreSQL bin path
$env:Path += ";C:\Program Files\PostgreSQL\14\bin"

# Create SQL script for database setup
$setupSql = @"
-- Create database
CREATE DATABASE sponge;

-- Create user
CREATE USER sponge WITH PASSWORD 'sponge_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE sponge TO sponge;
"@

$setupSql | & "C:\Program Files\PostgreSQL\14\bin\psql.exe" -U postgres -d postgres

# Enable pgvector extension
$vectorSql = @"
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO sponge;
"@

$vectorSql | & "C:\Program Files\PostgreSQL\14\bin\psql.exe" -U postgres -d sponge

Write-Host "PostgreSQL database configured successfully!"

# ================================================================
# 6. Create Python Virtual Environment
# ================================================================

Write-Host ""
Write-Host "[6/8] Creating Python virtual environment..."

# Remove existing venv if present
if (Test-Path "venv") {
    Remove-Item -Recurse -Force venv
}

# Create new venv
python -m venv venv

# Activate venv
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# ================================================================
# 7. Install Python Dependencies
# ================================================================

Write-Host ""
Write-Host "[7/8] Installing Python dependencies..."

pip install -r requirements.txt

# ================================================================
# 8. Initialize Database Schema
# ================================================================

Write-Host ""
Write-Host "[8/8] Initializing database schema..."

# Set PGPASSWORD environment variable
$env:PGPASSWORD = "sponge_secure_password"

# Run init script
& "C:\Program Files\PostgreSQL\14\bin\psql.exe" -h localhost -U sponge -d sponge -f database\init_db.sql

# Run seed data
& "C:\Program Files\PostgreSQL\14\bin\psql.exe" -h localhost -U sponge -d sponge -f database\seed_data.sql

# Clear PGPASSWORD
Remove-Item Env:\PGPASSWORD

# ================================================================
# Create Configuration File
# ================================================================

Write-Host ""
Write-Host "Creating configuration file..."

# Copy .env.example if .env doesn't exist
if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env file from .env.example"
    Write-Host "Please edit .env and configure your settings!"
} else {
    Write-Host ".env file already exists, skipping..."
}

# ================================================================
# Setup Complete
# ================================================================

Write-Host ""
Write-Host "============================================================"
Write-Host "Setup Complete!"
Write-Host "============================================================"
Write-Host ""
Write-Host "PostgreSQL Database:"
Write-Host "  - Host: localhost"
Write-Host "  - Port: 5432"
Write-Host "  - Database: sponge"
Write-Host "  - User: sponge"
Write-Host "  - Password: sponge_secure_password"
Write-Host ""
Write-Host "Python Environment:"
Write-Host "  - Virtual environment: venv\"
Write-Host "  - Python version: $(python --version)"
Write-Host ""
Write-Host "Windows Services:"
Write-Host "  - PostgreSQL: $(Get-Service postgresql-x64-14 | Select-Object Status,StartType)"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Activate virtual environment:"
Write-Host "     .\venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "  2. Edit configuration:"
Write-Host "     notepad .env"
Write-Host ""
Write-Host "  3. Run Sponge RCA:"
Write-Host "     python sponge_app.py --mode cli"
Write-Host ""
Write-Host "  4. Or run with Docker:"
Write-Host "     docker-compose up -d"
Write-Host ""
Write-Host "============================================================"
