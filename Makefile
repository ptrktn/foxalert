TEST_USER = user1

.PHONY: all
all:
	/bin/true

.PHONY: deps
deps:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

.PHONY: run
run:
	. venv/bin/activate && FLASK_APP=app.py flask run --host=0.0.0.0 --port=5000

.PHONY: init-db
init-db:
	. venv/bin/activate && FLASK_APP=app.py flask init-db

.PHONY: reset-db
reset-db:
	$(MAKE) -e DB_SCHEMA_RESET_ON_INIT=true init-db

.PHONY: sse-test
sse-test:
	curl -X POST http://localhost:5000/notifications/send \
	-H "Content-Type: application/json" \
	-d '{"title":"Server message","body":"Hello from server"}'

.PHONY: webpush-test
webpush-test:
	curl -X POST http://localhost:5000/push/send \
	-H "Content-Type: application/json" \
	-d '{"username":"$(TEST_USER)","title":"Hello","body":"Web Push test"}'

 # Get sample tracking data from around Narita Airport, Japan (35.7603892, 140.4076954) within 5km radius
 .PHONY: fetch-tracking-sample-data
fetch-tracking-sample-data:
	curl -v https://opendata.adsb.fi/api/v3/lat/35.7603892/lon/140.4076954/dist/10 | python3 -m json.tool > /var/tmp/nrt_adsbfi.json
	curl -v https://api.airplanes.live/v2/point/35.7603892/140.4076954/10 | python3 -m json.tool > /var/tmp/nrt_airplaneslive.json
