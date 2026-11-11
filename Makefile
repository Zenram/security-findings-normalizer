# Single-command entry points. Primary entry is `python3 main.py`.

PYTHON ?= python3

.PHONY: install run test clean ingest eval-retrieval evals evals-ci lint-testset

install:
	$(PYTHON) -m pip install -r requirements.txt

# Full pipeline: extract across model x prompt x sampling, score, write results/.
# Primary command is `python3 main.py`; this target just wraps it.
run:
	$(PYTHON) main.py

# Pass extra args through, e.g.:  make run-args ARGS="--models gemini"
run-args:
	$(PYTHON) main.py $(ARGS)

# --- Part 2 (RAG) ------------------------------------------------------------
ingest:
	$(PYTHON) main.py --ingest

eval-retrieval:
	$(PYTHON) main.py --eval-retrieval

# Deterministic + judged evals (judged needs GEMINI_API_KEY).
evals:
	$(PYTHON) main.py --evals --judge

# CI entry: lint the testset, then deterministic + judged evals with the gate.
evals-ci:
	$(PYTHON) main.py --evals --lint
	$(PYTHON) main.py --evals --judge --gate

lint-testset:
	$(PYTHON) main.py --evals --lint

test:
	$(PYTHON) -m pytest -q

clean:
	rm -rf results/raw results/metrics.json results/REPORT_DATA.json __pycache__ .pytest_cache
	touch results/.gitkeep
