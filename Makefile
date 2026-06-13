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

.PHONY: sse-test
sse-test:
	curl -X POST http://localhost:5000/notifications/send \
  -H "Content-Type: application/json" \
  -d '{"title":"Server message","body":"Hello from server"}'

.PHONY: webpush-test
webpush-test:
	curl -X POST http://localhost:5000/push/send \
	-H "Content-Type: application/json" \
	-d '{"username":"user1","title":"Hello","body":"Web Push test"}'
