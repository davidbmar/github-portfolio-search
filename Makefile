.PHONY: install test index clean

install:
	pip install -e ".[dev]"

test:
	python3 -m pytest tests/ -v

index:
	@echo "Usage: make index USER=<github-username>"
	@test -n "$(USER)" || (echo "Error: USER is required" && exit 1)
	ghps index $(USER)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true
