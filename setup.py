"""
Setup configuration for Sponge - AI Root Cause Analysis Tool
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r') as f:
        requirements = [
            line.strip() for line in f
            if line.strip() and not line.startswith('#')
        ]

setup(
    name="sponge-rca",
    version="1.0.0",
    author="Sponge Development Team",
    author_email="dev@sponge-rca.com",
    description="Machine Learning-powered log analysis and error resolution system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BarQode/Sponge",
    project_urls={
        "Bug Tracker": "https://github.com/BarQode/Sponge/issues",
        "Documentation": "https://github.com/BarQode/Sponge/wiki",
        "Source Code": "https://github.com/BarQode/Sponge",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Logging",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "build": [
            "pyinstaller>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "sponge=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "log analysis",
        "root cause analysis",
        "machine learning",
        "error detection",
        "tensorflow",
        "monitoring",
        "devops",
        "sre"
    ],
)
