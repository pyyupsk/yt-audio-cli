.PHONY: install dev lint format check typecheck security test test-cov clean all

# Install production dependencies
install:
	uv sync --no-dev

# Install all dependencies including dev
dev:
	uv sync

# Run linter
lint:
	uv run ruff check src/ tests/

# Run formatter
format:
	uv run ruff format src/ tests/

# Check formatting without modifying
check:
	uv run ruff format --check src/ tests/
	uv run ruff check src/ tests/

# Run type checker
typecheck:
	uv run pyright src/

# Run security scanner
security:
	uv run bandit -r src/

# Run tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov --cov-report=term-missing

# Run all CI checks
ci: check typecheck security test

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Default target
all: dev lint typecheck test
