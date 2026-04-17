PYTHON := python3
PIP := pip3

MAIN := main.py
DEFAULT_MAP := maps/valid/easy_map_01.txt
MAP ?= $(DEFAULT_MAP)

FLAKE8 := flake8 .
MYPY := mypy .
MYPY_FLAGS := --warn-return-any \
              --warn-unused-ignores \
              --ignore-missing-imports \
              --disallow-untyped-defs \
              --check-untyped-defs
MYPY_STRICT_FLAGS := --strict

PYC_PATTERN := *.pyc

.PHONY: install run debug clean lint lint-strict

install:
	@echo "Installing project dependencies..."
	@$(PIP) install -r requirements.txt
	@echo "Dependencies installed successfully."

run:
	@echo "Running simulation with map: $(MAP)"
	@$(PYTHON) $(MAIN) $(MAP)

debug:
	@echo "Starting debug mode with map: $(MAP)"
	@$(PYTHON) -m pdb $(MAIN) $(MAP)

clean:
	@echo "Cleaning cache and temporary files..."
	@find . -type d \( -name "__pycache__" -o -name ".mypy_cache" -o -name ".pytest_cache" -o -name ".ruff_cache" \) -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "$(PYC_PATTERN)" -delete 2>/dev/null || true
	@echo "Project cleaned."

lint:
	@echo "Running flake8..."
	@$(FLAKE8)
	@echo "Running mypy..."
	@$(MYPY) $(MYPY_FLAGS)
	@echo "Lint checks passed."

lint-strict:
	@echo "Running flake8..."
	@$(FLAKE8)
	@echo "Running mypy in strict mode..."
	@$(MYPY) $(MYPY_STRICT_FLAGS)
	@echo "Strict lint checks passed."
