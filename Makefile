.PHONY: all
all:
	/bin/true

.PHONY: deps
deps:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

.PHONY: run
run:
	. venv/bin/activate && python app.py

