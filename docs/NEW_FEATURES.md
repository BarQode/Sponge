# Sponge v2.0 - New Features Documentation

## Overview

Sponge v2.0 introduces powerful new capabilities for ML training, knowledge base management, and workflow automation. All features remain **100% free and open-source**.

---

## 🤖 ML Training Pipeline

### Features

Train custom ML models on your own monitoring data from CloudWatch, DataDog, Dynatrace, and other platforms.

### Data Import

Import data from multiple sources:

```python
from src.ml_training import DataImporter

importer = DataImporter()

# Import from CloudWatch
cloudwatch_data = [...]  # Your CloudWatch logs
df = importer.import_from_cloudwatch(cloudwatch_data)

# Import from DataDog
datadog_data = [...]  # Your DataDog logs
df = importer.import_from_datadog(datadog_data)

# Import from file (JSON, CSV, Parquet)
df = importer.import_from_file('monitoring_data.json')

# Validate data quality
report = importer.validate_training_data(df)
print(report)
```

### Model Training

Train models on your data:

```python
from src.ml_training import ModelTrainer

trainer = ModelTrainer(model_dir='models')

# Train text classifier (for issue categorization)
results = trainer.train_text_classifier(
    df,
    target_column='issue_type',
    text_column='message'
)

# Train anomaly detector (for metric analysis)
results = trainer.train_anomaly_detector(
    df,
    metric_columns=['cpu_usage', 'memory_usage']
)

# Train clustering model (for log grouping)
results = trainer.train_clustering_model(df)
```

### Complete Training Pipeline

```python
from src.ml_training import TrainingPipeline

pipeline = TrainingPipeline()

# Run complete training on exported monitoring data
results = pipeline.run_complete_training(
    data_source='exported_logs.json',
    source_type='file',
    models_to_train=['text_classifier', 'anomaly_detector', 'clustering']
)

# Train on directory of exports
results = pipeline.train_on_monitoring_exports(
    export_dir='monitoring_exports/',
    platform='cloudwatch'
)

# Incremental training with new data
results = pipeline.retrain_models('new_data.json')
```

---

## 📊 Enhanced Knowledge Base

### Advanced Filtering

Filter knowledge base entries with powerful queries:

```python
from src.knowledge_base import EnhancedKnowledgeBase

kb = EnhancedKnowledgeBase('data/knowledge_base.xlsx')

# Search with filters
filter_config = {
    'categories': ['CPU', 'Memory'],
    'severities': ['critical', 'high'],
    'min_confidence': 0.8,
    'has_solution': True,
    'recent_days': 30,
    'keywords': ['memory', 'leak']
}

results = kb.search(filter_config)
print(f"Found {len(results)} matching entries")
```

### User Selection

Mark and track selected entries:

```python
# Select individual entries
kb.add_user_selection("Memory leak in process", selected=True, notes="High priority")

# Bulk select based on filters
count = kb.bulk_select(
    filter_config={'severities': ['critical']},
    action='select'
)
print(f"Selected {count} critical issues")

# Get selected entries
selected = kb.get_selected_entries()
```

### Export Capabilities

Export in multiple formats:

```python
from src.knowledge_base import KnowledgeBaseExporter

exporter = KnowledgeBaseExporter('exports')

# Export to different formats
exporter.export_to_excel(results, 'filtered_results.xlsx')
exporter.export_to_csv(results, 'filtered_results.csv')
exporter.export_to_json(results, 'filtered_results.json')
exporter.export_to_html(results, 'filtered_results.html')
exporter.export_to_markdown(results, 'filtered_results.md')

# Export summary report
stats = kb.get_summary_stats(filter_config)
exporter.export_summary_report(results, 'summary_report.md', stats)

# Export by category (separate files)
files = exporter.export_by_category(results)

# Export automation-ready format
exporter.export_automation_ready(results, 'automation_data.json')
```

### Statistics and Recommendations

```python
# Get summary statistics
stats = kb.get_summary_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"By category: {stats['by_category']}")
print(f"By severity: {stats['by_severity']}")

# Get recommendations for most impactful issues
recommendations = kb.get_recommendations(top_n=5)
for rec in recommendations:
    print(f"Priority: {rec['issue_type']} (Impact score: {rec['impact_score']})")
```

---

## 🔧 Workflow Automation

### Generate Automation Workflows

Create automation workflows for detected issues:

```python
from src.automation import WorkflowGenerator

generator = WorkflowGenerator('workflows')

# Issue data from knowledge base
issue = {
    'Error_Pattern': 'Memory leak in application',
    'Category': 'Memory',
    'Severity': 'critical',
    'Issue_Type': 'memory_leak',
    'Implementation_Steps': json.dumps([
        'Check memory usage',
        'Identify leaking process',
        'Restart service'
    ])
}

# Generate bash workflow
workflow = generator.generate_workflow(issue, 'bash')

# Generate Python workflow
workflow = generator.generate_workflow(issue, 'python')

# Generate Ansible playbook
workflow = generator.generate_workflow(issue, 'ansible')

# Generate Docker workflow
workflow = generator.generate_workflow(issue, 'docker')
```

### Export Workflow Bundles

```python
# Export complete workflow bundle
bundle_path = generator.export_workflow_bundle(workflow)

# Bundle includes:
# - workflow.json (workflow specification)
# - workflow_script.sh or .py (executable script)
# - Dockerfile (for containerization)
# - README.md (usage instructions)
```

### Execute Workflows

```python
from src.automation import AutomationEngine

engine = AutomationEngine(dry_run=True)

# Execute workflow
result = engine.execute_workflow(workflow)

print(f"Status: {result['status']}")
print(f"Steps completed: {result['steps_completed']}/{result['total_steps']}")

# Execute in Docker container
result = engine.execute_docker_workflow(bundle_path)

# Get execution history
history = engine.get_execution_history(limit=10)
```

### Script Templates

Use pre-built templates for common issues:

```python
from src.automation import ScriptTemplates

# Get template for memory leak fix
bash_script = ScriptTemplates.get_template('memory_leak', 'bash')
python_script = ScriptTemplates.get_template('memory_leak', 'python')

# Available templates:
# - memory_leak
# - high_cpu
# - zombie_process
# - disk_space
# - log_rotation
# - database_slow
# - network_issue
```

---

## 🐳 Docker Deployment

### Production Dockerfile

```bash
# Build production image
docker build -f Dockerfile.production -t sponge:2.0.0 .

# Run with volume mounts
docker run -v $(pwd)/data:/app/data \
           -v $(pwd)/models:/app/models \
           -e AWS_REGION=us-east-1 \
           sponge:2.0.0 --mode performance
```

### Docker Compose

```bash
# Start with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f sponge

# Stop services
docker-compose down
```

---

## 💻 Desktop Applications

### Windows

Build Windows installer:

```bash
# Install dependencies
pip install pyinstaller

# Build installer
python build_windows_installer.py

# Output: Sponge-2.0.0-setup.exe
```

### MacOS

Build MacOS installer:

```bash
# Install dependencies
pip install pyinstaller
brew install create-dmg  # For DMG creation

# Build installer
python build_macos_installer.py

# Output: Sponge-2.0.0.dmg or Sponge-2.0.0.pkg
```

---

## 🧪 Testing

### Run All Tests

```bash
# Run complete test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test modules
pytest tests/test_ml_training.py -v
pytest tests/test_knowledge_base.py -v
pytest tests/test_automation.py -v
```

### Integration Tests

```bash
# Run integration tests
pytest tests/ -v -m integration

# Run performance tests
pytest tests/ -v -m performance
```

---

## 📚 Usage Examples

### Complete Workflow Example

```python
# 1. Import monitoring data
from src.ml_training import DataImporter

importer = DataImporter()
df = importer.import_from_file('cloudwatch_export.json')

# 2. Train models
from src.ml_training import TrainingPipeline

pipeline = TrainingPipeline()
results = pipeline.run_complete_training(
    'cloudwatch_export.json',
    models_to_train=['text_classifier', 'anomaly_detector']
)

# 3. Search knowledge base
from src.knowledge_base import EnhancedKnowledgeBase

kb = EnhancedKnowledgeBase()
critical_issues = kb.search({
    'severities': ['critical'],
    'has_solution': True
})

# 4. Generate automation workflows
from src.automation import WorkflowGenerator

generator = WorkflowGenerator()
for _, issue in critical_issues.iterrows():
    workflow = generator.generate_workflow(issue.to_dict(), 'bash')
    bundle = generator.export_workflow_bundle(workflow)
    print(f"Workflow bundle created: {bundle}")

# 5. Execute workflows (dry run)
from src.automation import AutomationEngine

engine = AutomationEngine(dry_run=True)
result = engine.execute_workflow(workflow)
print(f"Execution result: {result['status']}")
```

---

## 🔄 Migration Guide

### From v1.0 to v2.0

#### Knowledge Base Compatibility

v2.0 is fully backward compatible with v1.0 knowledge bases. Simply use the enhanced class:

```python
# Old way (still works)
from src.storage import KnowledgeBase
kb = KnowledgeBase()

# New way (recommended)
from src.knowledge_base import EnhancedKnowledgeBase
kb = EnhancedKnowledgeBase()
```

#### New Dependencies

Install new dependencies:

```bash
pip install -r requirements.txt
```

---

## 📋 Configuration

### Environment Variables

```bash
# Knowledge Base
export KB_FILE=/path/to/knowledge_base.xlsx

# Model Directory
export MODEL_DIR=/path/to/models

# Workflow Directory
export WORKFLOW_DIR=/path/to/workflows

# Export Directory
export EXPORT_DIR=/path/to/exports

# Monitoring Credentials
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export DATADOG_API_KEY=your_key
export DATADOG_APP_KEY=your_app_key
```

---

## 🆘 Troubleshooting

### Common Issues

**Issue**: Model training fails with "Insufficient data"
**Solution**: Ensure you have at least 100 labeled samples for supervised learning

**Issue**: Workflow execution fails
**Solution**: Check that scripts have execute permissions: `chmod +x workflow_script.sh`

**Issue**: Docker container can't access logs
**Solution**: Mount log directory as volume: `-v /var/log:/var/log:ro`

---

## 🔗 API Reference

See individual module documentation:
- [ML Training API](API_ML_TRAINING.md)
- [Knowledge Base API](API_KNOWLEDGE_BASE.md)
- [Automation API](API_AUTOMATION.md)

---

**All features are 100% free and open-source under MIT License!**
