# Architecture & Project Structure

## Directory Layout
\\\
project/
├── src/              # Source code
├── tests/            # Test files
├── docs/             # Documentation
├── .roo/             # AI workflow rules
│   ├── rules/        # Guidelines and standards
│   ├── prompts/      # Prompt templates
│   └── results/      # Output and results
├── requirements.txt  # Production dependencies
├── dev-requirements.txt  # Development dependencies
└── CLAUDE.md         # AI context and preferences
\\\

## Module Organization
- Keep modules focused on single responsibility
- Use meaningful package names
- Avoid circular imports
- Export public API from __init__.py

## Dependencies
- Minimal external dependencies for production
- Development dependencies separated
- Regular updates and security patches
- Version pinning for reproducibility

## Configuration
- Use environment variables for sensitive data
- Separate config from code
- Support multiple environments (dev, test, prod)
