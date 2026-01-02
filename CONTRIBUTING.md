# Contributing to Sponge

Thank you for your interest in contributing to Sponge! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/BarQode/Sponge.git
cd Sponge

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests to verify setup
python -m pytest tests/ -v
```

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, readable code
   - Follow Python PEP 8 style guide
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests**
   ```bash
   python -m pytest tests/ -v
   ```

4. **Format code**
   ```bash
   black src/ tests/
   flake8 src/ tests/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Go to GitHub and create a PR
   - Describe your changes
   - Link any related issues

## Code Style

- Follow PEP 8
- Use type hints where possible
- Write docstrings for all public functions/classes
- Keep functions focused and small
- Add comments for complex logic

## Testing

- Write unit tests for all new features
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use mocks for external dependencies

## Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Include tests for your changes
- Update documentation as needed
- Ensure all tests pass
- Respond to review comments promptly

## Questions?

Open an issue for questions or clarifications.
