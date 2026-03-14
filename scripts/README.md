# Sponge RCA Platform - Setup Scripts

This directory contains platform-specific setup scripts for deploying Sponge RCA on various operating systems and hardware platforms.

## Available Scripts

### Linux (`setup-linux.sh`)
**Supported Distributions:**
- Ubuntu 20.04+
- Debian 11+
- CentOS 8+
- Fedora 35+

**Usage:**
```bash
chmod +x scripts/setup-linux.sh
./scripts/setup-linux.sh
```

**What it does:**
- Installs PostgreSQL 14+ with pgvector extension
- Sets up Python 3.10+ virtual environment
- Installs all required dependencies
- Initializes database schema
- Creates sample configuration file

---

### macOS (`setup-macos.sh`)
**Supported Versions:**
- macOS 10.15 (Catalina) or later
- Requires Homebrew package manager

**Usage:**
```bash
chmod +x scripts/setup-macos.sh
./scripts/setup-macos.sh
```

**What it does:**
- Installs/updates Homebrew
- Installs PostgreSQL 14+ with pgvector via Homebrew
- Sets up Python 3.10+ virtual environment
- Configures PostgreSQL service
- Initializes database and seeds sample data

---

### Windows (`setup-windows.ps1`)
**Supported Versions:**
- Windows 10/11
- Windows Server 2019+
- Requires PowerShell 5.1+

**Usage:**
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\setup-windows.ps1
```

**What it does:**
- Installs Chocolatey package manager
- Installs PostgreSQL 14+ with pgvector
- Installs Python 3.10+ and Visual C++ Build Tools
- Configures PostgreSQL service
- Creates Python virtual environment
- Initializes database schema

---

### Raspberry Pi (`setup-raspberry-pi.sh`)
**Supported Models:**
- Raspberry Pi 3B+ (ARMv7)
- Raspberry Pi 4 (ARM64)
- Raspberry Pi 5 (ARM64)
- Raspberry Pi OS (Bullseye or later)

**Usage:**
```bash
chmod +x scripts/setup-raspberry-pi.sh
./scripts/setup-raspberry-pi.sh
```

**What it does:**
- Compiles and installs pgvector from source
- Sets up ARM-optimized Python environment
- Installs lightweight dependencies
- Applies PostgreSQL performance tuning for RPi
- Configures memory-optimized settings

**Note**: Setup may take 15-30 minutes on older Raspberry Pi models due to compilation.

---

## Docker Deployment

For all platforms, you can also use Docker for simplified deployment:

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # or notepad .env on Windows

# Start all services
docker-compose up -d
```

**Services included:**
- Sponge RCA application
- PostgreSQL 14 with pgvector
- Prometheus (metrics)
- Grafana (visualization)
- Redis (caching)

---

## Post-Installation Steps

After running any setup script:

### 1. Activate Virtual Environment

**Linux/macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Configure Environment

Edit the `.env` file with your settings:
```bash
# Linux/macOS
nano .env

# Windows
notepad .env
```

**Required settings:**
- PostgreSQL credentials
- Platform integration API keys
- Log levels and ports

### 3. Verify Installation

```bash
# Test database connection
python -c "from src.database.postgres_vector import PostgresVectorDB; db = PostgresVectorDB(); print('✅ Database connected')"

# Test KNN model
python -c "from src.ml.knn_detector import KNNErrorDetector; print('✅ KNN module loaded')"

# Test platform integrations
python -c "from src.integrations import list_available_platforms; print(f'✅ {len(list_available_platforms())} platforms available')"
```

### 4. Run Sponge RCA

```bash
# CLI mode (interactive)
python sponge_app.py --mode cli

# Monitoring mode (continuous)
python sponge_app.py --mode monitor

# SOAP API mode (web service)
python sponge_app.py --mode soap

# Training mode (ML model training)
python sponge_app.py --mode training
```

---

## Troubleshooting

### PostgreSQL Connection Issues

**Error**: `could not connect to server`

**Solution**:
```bash
# Linux/macOS
sudo systemctl status postgresql
sudo systemctl start postgresql

# Windows (PowerShell as Admin)
Get-Service postgresql-x64-14
Start-Service postgresql-x64-14
```

### pgvector Extension Not Found

**Error**: `extension "vector" is not available`

**Solution**:
```sql
-- Connect as postgres superuser
psql -U postgres -d sponge

-- Check available extensions
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- Install pgvector manually (see setup script for your platform)
```

### Python Package Installation Fails

**Error**: `Failed building wheel for [package]`

**Linux/macOS Solution**:
```bash
# Install build tools
sudo apt-get install python3-dev build-essential  # Ubuntu/Debian
brew install gcc                                   # macOS
```

**Windows Solution**:
```powershell
# Install Visual Studio Build Tools
choco install visualstudio2022buildtools -y
```

### Raspberry Pi Performance Issues

**Issue**: Slow ML model training

**Solutions**:
1. Use pre-trained models instead of training from scratch
2. Reduce dataset size for training
3. Use external SSD for better I/O
4. Overclock (if cooling is adequate)
5. Use Docker for better resource management

---

## Security Notes

### Change Default Passwords

After setup, change the default PostgreSQL password:

```sql
-- Connect as postgres
psql -U postgres

-- Change sponge user password
ALTER USER sponge WITH PASSWORD 'your_new_secure_password';
```

Update `.env` file with new password:
```bash
POSTGRES_PASSWORD=your_new_secure_password
```

### Firewall Configuration

**Linux (UFW)**:
```bash
sudo ufw allow 5432/tcp  # PostgreSQL
sudo ufw allow 8080/tcp  # Sponge API
sudo ufw allow 9090/tcp  # Prometheus
```

**Windows (PowerShell as Admin)**:
```powershell
New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -Port 5432 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Sponge API" -Direction Inbound -Port 8080 -Protocol TCP -Action Allow
```

---

## Platform-Specific Notes

### macOS: Homebrew Permissions

If you encounter permission issues:
```bash
sudo chown -R $(whoami) $(brew --prefix)/*
```

### Windows: Execution Policy

If scripts won't run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Raspberry Pi: Swap Space

For better performance on models with <4GB RAM:
```bash
# Increase swap to 2GB
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## Getting Help

- **Documentation**: See [README.md](../README.md)
- **Issues**: https://github.com/BarQode/Sponge/issues
- **Platform Guides**: See [LOG_PLATFORMS.md](../LOG_PLATFORMS.md)

---

**Last Updated**: 2026-03-14
