# 🧽 Sponge - AI Root Cause Analysis Tool

**Open-Source, Machine Learning-Powered Log Analysis & Performance Monitoring**

Sponge is a free, open-source tool that uses advanced ML (TensorFlow, PyTorch, Scikit-learn) to automatically analyze system logs, identify performance issues, and provide intelligent solutions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15+-orange.svg)](https://www.tensorflow.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org/)

---

## 🌟 Features

### Core Capabilities
- 🤖 **Hybrid ML Engine** - TensorFlow + PyTorch + Scikit-learn
- 🔍 **Intelligent Pattern Recognition** - Semantic log analysis with LSTM + Attention
- 📊 **Performance Analysis** - CPU, Memory, Latency, and Zombie process detection
- 🌐 **Web Scraping** - Automatic solution discovery from StackOverflow and technical sources
- 💾 **Knowledge Base** - Local Excel spreadsheet for caching solutions
- ⚡ **Multiple Integrations** - CloudWatch, DataDog, Dynatrace, Splunk, and more

### Advanced Features
- **Memory Leak Detection** - Correlation analysis to identify gradual memory increases
- **Anomaly Detection** - PyTorch autoencoder for metric anomalies
- **Zombie Process Detection** - Identify orphaned resources and stuck threads
- **Detailed Fix Steps** - Step-by-step implementation instructions
- **Multi-Platform** - Local installation, Docker, or Kubernetes deployment

---

## 🚀 Quick Start

### Option 1: Local Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run with mock data
python main.py

# Analyze your own logs
python main.py --mode errors --source file --file /var/log/app.log

# Performance analysis mode
python main.py --mode performance --integration mock
```

### Option 2: Docker

```bash
# Build the image
docker build -t sponge:latest .

# Run the container
docker run -v $(pwd)/data:/app/data sponge:latest
```

### Option 3: Windows Executable

```bash
# Build executable
pip install pyinstaller
python build_exe.py

# Run from dist/ folder
./dist/Sponge-RCA-v1.0.exe
```

---

## 💻 Usage

### Error Analysis Mode (Original)

```bash
# Analyze logs from file
python main.py --mode errors --source file --file application.log

# View knowledge base statistics
python main.py --stats

# Export knowledge base to CSV
python main.py --export results.csv

# Show top 10 errors
python main.py --top 10
```

### Performance Analysis Mode (New!)

```bash
# Analyze with mock data (testing)
python main.py --mode performance --integration mock

# Analyze AWS CloudWatch logs
python main.py --mode performance --integration cloudwatch \
  --aws-key YOUR_KEY \
  --aws-secret YOUR_SECRET \
  --log-group /aws/lambda/my-function

# Analyze DataDog metrics
python main.py --mode performance --integration datadog \
  --datadog-api-key YOUR_KEY \
  --datadog-app-key YOUR_APP_KEY
```

---

## 🧠 ML Architecture

Sponge uses a hybrid approach combining three frameworks:

### TensorFlow
- **Text Encoding**: LSTM with attention mechanism
- **Pattern Recognition**: Semantic analysis of log messages
- **Use Case**: Natural language understanding of errors

### PyTorch
- **Anomaly Detection**: Autoencoder architecture
- **Metric Analysis**: Reconstruction error for outlier detection
- **Use Case**: Performance metric anomaly identification

### Scikit-learn
- **Clustering**: DBSCAN for log grouping
- **Classification**: Random Forest for issue categorization
- **Outlier Detection**: Isolation Forest
- **Use Case**: Traditional ML tasks and ensembles

---

## 📊 What It Detects

### CPU Issues
- ✅ High sustained usage (>80%)
- ✅ CPU spikes and bursts
- ✅ Gradual increases (memory leak indicators)
- ✅ Thread contention

### Memory Issues
- ✅ **Memory leaks** (correlation analysis)
- ✅ High memory usage
- ✅ Out of Memory errors
- ✅ **Zombie processes** holding memory

### Latency Issues
- ✅ High response times
- ✅ Latency spikes
- ✅ Timeout errors
- ✅ Database query slowness

### Resource Leaks
- ✅ Defunct processes
- ✅ Orphaned connections
- ✅ File handle leaks
- ✅ Stuck threads

---

## 🔌 Integrations

### Monitoring Platforms

**Production Ready:**
- ✅ **AWS CloudWatch** - Full log and metrics integration
- ✅ **DataDog** - API integration with scoring
- ✅ **Dynatrace** - Performance monitoring

**Supported (Framework Ready):**
- Splunk
- Azure Monitor
- Elastic Observability
- Grafana
- Sentry
- Coralogix
- Lumigo
- Huntress

---

## 🐳 Advanced Deployment

### Kubernetes (Optional)

For production deployments on Kubernetes:

```bash
# Deploy to existing K8s cluster
kubectl apply -f kubernetes/

# Or use Helm (coming soon)
helm install sponge ./charts/sponge
```

See `docs/DEPLOYMENT_GUIDE.md` for complete Kubernetes setup.

### AWS EKS (Optional)

Infrastructure as Code with Terraform:

```bash
cd terraform
terraform init
terraform apply
```

**Note:** This is optional for advanced users. The tool works perfectly as a standalone CLI application.

---

## 📁 Project Structure

```
Sponge/
├── src/
│   ├── analyzers/              # Performance analyzers
│   │   ├── cpu_analyzer.py     # CPU analysis
│   │   ├── memory_analyzer.py  # Memory leak detection
│   │   ├── latency_analyzer.py # Latency analysis
│   │   └── zombie_detector.py  # Resource leak detection
│   ├── integrations/           # Platform integrations
│   │   ├── aws_cloudwatch.py
│   │   ├── datadog.py
│   │   └── dynatrace.py
│   ├── ml_engine.py            # Original ML clustering
│   ├── scraper.py              # Solution scraper
│   └── storage.py              # Knowledge base
├── backend/
│   └── models/
│       └── hybrid_ml_engine.py # TF/PyTorch/Sklearn ML
├── tests/                      # Comprehensive test suite
├── kubernetes/                 # Optional K8s manifests
├── terraform/                  # Optional IaC
└── main.py                     # Main application
```

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html

# Test specific component
python -m pytest tests/test_analyzers.py -v
```

---

## 🛠️ Development

### Prerequisites
- Python 3.9+
- TensorFlow 2.15+
- PyTorch 2.0+
- 4GB RAM minimum

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Format code
black src/ tests/

# Lint
flake8 src/ tests/
```

---

## 📖 Documentation

- **[Architecture Overview](docs/ARCHITECTURE_AND_COST_ANALYSIS.md)** - System design and components
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Kubernetes and cloud deployment
- **[Complete Guide](docs/COMPLETE_SAAS_PLATFORM_SUMMARY.md)** - Comprehensive documentation

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Submit pull requests
- ⭐ Star the project

### Development Process
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**Free to use, modify, and distribute - even commercially!**

---

## 🙏 Acknowledgments

- **TensorFlow** team for the ML framework
- **PyTorch** team for the deep learning library
- **Scikit-learn** for classical ML algorithms
- **DuckDuckGo** for the search API
- **Open-source community** for inspiration and support

---

## 🎯 Use Cases

### DevOps Teams
- Automated log analysis in CI/CD pipelines
- Performance monitoring for applications
- Root cause analysis during incidents

### SRE Teams
- Proactive issue detection
- Incident response acceleration
- Knowledge base building

### Developers
- Local debugging with ML-powered insights
- Performance optimization
- Learning from common error patterns

### System Administrators
- Server health monitoring
- Resource leak detection
- Automated troubleshooting

---

## 🔮 Roadmap

- [ ] Web UI dashboard (React)
- [ ] Real-time log streaming
- [ ] Additional ML models (BERT, GPT-based)
- [ ] More integrations (Prometheus, Loki, etc.)
- [ ] Automated remediation suggestions
- [ ] Plugin system for custom analyzers
- [ ] Multi-language support
- [ ] Mobile app

---

## 💬 Community & Support

- **Issues**: [GitHub Issues](https://github.com/BarQode/Sponge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/BarQode/Sponge/discussions)
- **Documentation**: [Wiki](https://github.com/BarQode/Sponge/wiki)

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

## 📊 Performance

- **Logs analyzed per second**: ~1,000
- **Memory usage**: ~500MB base
- **Startup time**: <5 seconds
- **ML inference time**: <100ms per log

---

## 🔒 Security

- No external data transmission (except web scraping)
- Local knowledge base storage
- No telemetry or tracking
- API keys stored locally only
- Secrets management via environment variables

---

## ⚡ Quick Examples

### Example 1: Analyze Application Logs
```bash
python main.py --mode errors --source file --file app.log
```

### Example 2: Detect Memory Leaks
```bash
python main.py --mode performance --integration mock
```

### Example 3: Build Knowledge Base
```bash
# Analyze logs over time
for log in logs/*.log; do
    python main.py --source file --file "$log"
done

# Export accumulated knowledge
python main.py --export knowledge.csv
```

---

**Built with ❤️ for the DevOps and SRE community**

**100% Free and Open Source - Forever!** 🎉
