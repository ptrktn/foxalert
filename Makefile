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

.PHONY: sse
sse:
	curl -X POST http://localhost:5000/notifications/send \
  -H "Content-Type: application/json" \
  -d '{"title":"Server message","body":"Hello from server"}'

