.PHONY: install test lint index serve export deploy clean

install:
	pip install -e ".[dev]"

test:
	python3 -m pytest tests/ -v

lint:
	python3 -m py_compile src/ghps/*.py

index:
	@echo "Usage: make index USER=<github-username>"
	@test -n "$(USER)" || (echo "Error: USER is required" && exit 1)
	ghps index $(USER)

serve:
	python3 -m uvicorn ghps.api:app --reload --port 8000

export:
	ghps export

deploy:
	@test -d web/ || (echo "Error: web/ directory not found" && exit 1)
	@test -f scripts/deploy.sh || (echo "Error: scripts/deploy.sh not found" && exit 1)
	bash scripts/deploy.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true
