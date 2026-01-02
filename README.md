# 🧽 Sponge - AI Root Cause Analysis Tool

**Machine Learning-Powered Log Analysis & Error Resolution System**

Sponge is a production-grade, local-installable software tool that uses TensorFlow to automatically analyze system logs, identify error patterns, and provide intelligent solutions by leveraging web scraping and building a local knowledge base.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15+-orange.svg)](https://www.tensorflow.org/)

---

## 🌟 Features

- **🤖 ML-Powered Analysis**: Uses TensorFlow and DBSCAN clustering to identify root causes
- **🔍 Intelligent Pattern Recognition**: Automatically normalizes logs (IPs, timestamps, hex values) to find true error patterns
- **🌐 Web Scraping**: Searches StackOverflow and other trusted sources for solutions
- **📊 Knowledge Base**: Maintains local Excel spreadsheet cache to avoid redundant searches
- **⚡ Fast & Efficient**: Local processing with no external API dependencies (except web search)
- **🐳 Docker Support**: Containerized deployment for easy integration
- **💻 Windows Executable**: Build standalone .exe for easy distribution
- **📈 Statistics & Reporting**: Track error patterns and resolution effectiveness

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Sponge RCA Tool                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │ Log Ingestion│──▶│  ML Engine   │──▶│   Scraper    │   │
│  │              │   │ (TensorFlow) │   │  (DuckDuckGo)│   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│         │                  │                    │          │
│         │                  ▼                    │          │
│         │          ┌──────────────┐             │          │
│         └─────────▶│ Knowledge    │◀────────────┘          │
│                    │ Base (Excel) │                        │
│                    └──────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **ML Engine** (`src/ml_engine.py`): TensorFlow-based semantic log clustering
2. **Web Scraper** (`src/scraper.py`): Intelligent solution finder with retry logic
3. **Knowledge Base** (`src/storage.py`): Excel-based cache with deduplication
4. **Main Application** (`main.py`): CLI interface and workflow orchestration

---

## 📋 Requirements

- Python 3.9 or higher
- 4GB RAM minimum
- Internet connection (for web scraping)

---

## 🚀 Quick Start

### Installation

#### Option 1: Using pip (Recommended)

```bash
# Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# Install in development mode
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt
```

#### Option 2: Using Docker

```bash
# Build the Docker image
docker build -t sponge-rca:latest .

# Run the container
docker run -v $(pwd)/data:/app/data sponge-rca:latest
```

#### Option 3: Windows Executable

```bash
# Build the executable
python build_exe.py

# Find the .exe in the dist/ folder
# Double-click to run!
```

---

## 💻 Usage

### Basic Usage

```bash
# Run with mock data (for testing)
python main.py

# Analyze logs from a file
python main.py --source file --file /path/to/logs.txt

# Show knowledge base statistics
python main.py --stats

# Export knowledge base to CSV
python main.py --export results.csv

# View top 10 errors
python main.py --top 10
```

### Advanced Usage

```bash
# Set custom knowledge base location
export KB_FILE=/path/to/custom_kb.xlsx
python main.py

# Adjust ML clustering parameters
export CLUSTERING_EPS=0.3
export CLUSTERING_MIN_SAMPLES=3
python main.py

# Configure scraper settings
export SCRAPER_RETRIES=5
export SCRAPER_MAX_RESULTS=5
python main.py
```

---

## 🧪 Testing

The project follows Test-Driven Development (TDD) principles.

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python tests/test_rca_tool.py
```

### Test Coverage

- ✅ ML Engine: Log cleaning, vectorization, clustering
- ✅ Web Scraper: Result scoring, retry logic, aggregation
- ✅ Knowledge Base: CRUD operations, caching, statistics
- ✅ Integration: Complete workflow end-to-end

---

## 📁 Project Structure

```
Sponge/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management
│   ├── ml_engine.py         # TensorFlow ML engine
│   ├── scraper.py           # Web scraping module
│   └── storage.py           # Excel knowledge base
├── tests/
│   ├── __init__.py
│   └── test_rca_tool.py     # Comprehensive test suite
├── data/                    # Data directory (created at runtime)
├── logs/                    # Application logs
├── models/                  # ML models (if saved)
├── main.py                  # Main application
├── setup.py                 # Package setup
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker configuration
├── build_exe.py             # Windows executable builder
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
└── README.md                # This file
```

---

## 🛠️ Building for Production

### Build Windows Executable

```bash
pip install pyinstaller
python build_exe.py
```

The executable will be created in `dist/Sponge-RCA-v1.0.exe`

### Build Docker Image

```bash
docker build -t sponge-rca:1.0.0 .
docker tag sponge-rca:1.0.0 sponge-rca:latest
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 💡 Suggested Stack Enhancements

### Recommended Additions

1. **Database Backend**: PostgreSQL/MongoDB for large-scale deployments
2. **API Server**: FastAPI REST API for remote access
3. **Web Dashboard**: React/Vue.js for visualization
4. **Alerting**: PagerDuty/Opsgenie integration
5. **Authentication**: OAuth2/JWT for multi-user support
6. **Caching Layer**: Redis for faster lookups
7. **Queue System**: RabbitMQ/Kafka for async processing
8. **Metrics**: Prometheus/Grafana integration
9. **CI/CD**: GitHub Actions for automated testing
10. **AI Improvements**: Fine-tune models on domain-specific logs

---

**Made with ❤️ for DevOps and SRE teams**
