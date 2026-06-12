.PHONY: all
all:
	/bin/true

.PHONY: deps
deps:
	python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	#. venv/bin/activate && pip3 install -I git+https://github.com/wbond/oscrypto.git

.PHONY: run
run:
	. venv/bin/activate && gunicorn -b 127.0.0.1:5000 -k eventlet -w 1 app:app

