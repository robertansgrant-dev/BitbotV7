# Coding Standards

## Python Code Style
- Follow PEP 8 guidelines
- Use 4 spaces for indentation
- Line length: maximum 100 characters
- Use type hints for function arguments and return types

## Naming Conventions
- Classes: PascalCase (e.g., MyClass)
- Functions/Methods: snake_case (e.g., my_function)
- Constants: UPPER_SNAKE_CASE (e.g., MAX_RETRY)
- Private methods: prefix with underscore (e.g., _private_method)

## Code Organization
- Group imports at the top: stdlib, third-party, local
- Use meaningful variable names
- Add docstrings to all functions and classes
- Keep functions focused and under 50 lines where possible

## Comments
- Use comments to explain WHY, not WHAT
- Update comments when code changes
- Use inline comments sparingly

## Testing
- Unit tests for all public functions
- Minimum 80% code coverage
- Use pytest framework
- File naming: test_*.py or *_test.py
