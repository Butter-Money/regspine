VENV := .venv
PY   := $(VENV)/bin/python
PY311 := /opt/homebrew/opt/python@3.11/bin/python3.11

.PHONY: dev ingest fixtures eval test lint clean

dev:                       ## create the venv and install the package
	$(PY311) -m venv $(VENV)
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -e ".[dev]"

ingest:                    ## run the deterministic pipeline over data/corpus
	$(PY) -m regspine.ingest.cli

fixtures:                  ## ingest and refresh the eval ground-truth fixtures
	$(PY) -m regspine.ingest.cli --fixtures

eval: test                 ## the CI gates (segmentation, anchors, ground truth)

test:
	$(PY) -m pytest tests/ -q

lint:
	$(PY) -m ruff check regspine tests

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
