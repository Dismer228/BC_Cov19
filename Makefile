PYTHON=python3

.PHONY: venv install explore eda ingest views

venv:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

install:
	. .venv/bin/activate && pip install -r requirements.txt

explore:
	. .venv/bin/activate && $(PYTHON) -m src.eda.explore_starschema

eda:
	. .venv/bin/activate && $(PYTHON) -m src.eda.automate_eda

ingest:
	. .venv/bin/activate && $(PYTHON) -m src.augment.worldbank_ingest

views:
	. .venv/bin/activate && $(PYTHON) -m src.augment.create_enriched_views
