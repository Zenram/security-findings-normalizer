# Single-command entry points. Primary entry is `python3 main.py`.

PYTHON ?= python3

.PHONY: install run test clean

install:
	$(PYTHON) -m pip install -r requirements.txt

# Full pipeline: extract across model x prompt x sampling, score, write results/.
# Primary command is `python3 main.py`; this target just wraps it.
run:
	$(PYTHON) main.py

# Pass extra args through, e.g.:  make run-args ARGS="--models gemini"
run-args:
	$(PYTHON) main.py $(ARGS)

test:
	$(PYTHON) -m pytest -q

clean:
	rm -rf results/raw results/metrics.json results/REPORT_DATA.json __pycache__ .pytest_cache
	touch results/.gitkeep
