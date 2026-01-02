"""
Configuration management for the RCA Tool.
Handles environment variables, API keys, and system settings.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Knowledge Base Configuration
KNOWLEDGE_BASE_FILE = os.getenv("KB_FILE", str(DATA_DIR / "error_knowledge_base.xlsx"))

# ML Engine Configuration
ML_CONFIG = {
    "max_tokens": int(os.getenv("ML_MAX_TOKENS", "5000")),
    "output_mode": "tf_idf",
    "clustering_eps": float(os.getenv("CLUSTERING_EPS", "0.5")),
    "clustering_min_samples": int(os.getenv("CLUSTERING_MIN_SAMPLES", "2")),
    "clustering_metric": "cosine"
}

# Web Scraper Configuration
SCRAPER_CONFIG = {
    "max_retries": int(os.getenv("SCRAPER_RETRIES", "3")),
    "retry_delay": float(os.getenv("SCRAPER_RETRY_DELAY", "2.0")),
    "max_results": int(os.getenv("SCRAPER_MAX_RESULTS", "3")),
    "timeout": int(os.getenv("SCRAPER_TIMEOUT", "10"))
}

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": str(LOGS_DIR / "rca_tool.log"),
            "mode": "a"
        }
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True
        }
    }
}

# Integration API Keys (from environment)
API_KEYS = {
    "datadog": os.getenv("DATADOG_API_KEY"),
    "datadog_app": os.getenv("DATADOG_APP_KEY"),
    "dynatrace": os.getenv("DYNATRACE_API_KEY"),
    "dynatrace_url": os.getenv("DYNATRACE_URL"),
    "splunk": os.getenv("SPLUNK_API_KEY"),
    "splunk_url": os.getenv("SPLUNK_URL"),
    "elasticsearch": os.getenv("ELASTICSEARCH_URL"),
    "elasticsearch_user": os.getenv("ELASTICSEARCH_USER"),
    "elasticsearch_pass": os.getenv("ELASTICSEARCH_PASS")
}

# Log Source Configuration
LOG_SOURCE = os.getenv("LOG_SOURCE", "mock")  # Options: mock, file, datadog, dynatrace, splunk, elasticsearch
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", str(DATA_DIR / "sample_logs.txt"))

# Performance Settings
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
MAX_LOGS_PER_RUN = int(os.getenv("MAX_LOGS_PER_RUN", "10000"))
