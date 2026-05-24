.PHONY: help install test lint format typecheck coverage security all clean watch smoke

help:
	@echo "wiki-toolkit — comandi rapidi (uv-based)"
	@echo ""
	@echo "  make install     Installa deps + dev extras"
	@echo "  make test        Esegue la suite pytest"
	@echo "  make lint        Lint con ruff (no fix)"
	@echo "  make format      Format con ruff"
	@echo "  make typecheck   mypy gradual"
	@echo "  make coverage    pytest + report HTML in htmlcov/"
	@echo "  make security    Scan no-secrets test"
	@echo "  make smoke       Smoke test E2E sul dataset pilota"
	@echo "  make all         lint + typecheck + test"
	@echo "  make clean       Rimuove cache pytest/mypy/ruff/coverage"
	@echo ""

install:
	uv sync --extra dev

test:
	uv run pytest tests/

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy wiki/ scanners/ extractors/ categorizers/ reconcilers/ batch_ui/ bootstrap/

coverage:
	uv run pytest tests/ --cov --cov-report=term-missing --cov-report=html
	@echo "Report HTML: htmlcov/index.html"

security:
	uv run pytest tests/test_no_secrets.py -v

smoke:
	uv run python -m tests.fixtures.build_pilot_dataset --output /tmp/wiki-smoke/_inbox/
	@echo "Dataset pilota generato in /tmp/wiki-smoke/_inbox/"
	@echo "Lancia manualmente: wiki scan/extract/categorize/reconcile/status --client pilot"

watch:
	@echo "wiki watch — modalità sempre in ascolto (Ctrl+C per fermare)"
	uv run wiki watch

all: lint typecheck test
	@echo ""
	@echo "Tutti i check passati."

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build *.egg-info .coverage
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
	@echo "Cache pulita."
