PYTHON=python3
PYTHONPATH=./
name=meetingbot

# for running from IDEs (e.g., TextMate)
.PHONY: run
run:
	$(PYTHON) $(name).py

.PHONY: lint
lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pylint *.py

.PHONY: black
black:
	PYTHONPATH=$(PYTHONPATH) black *.py

.PHONY: clean
clean:
	rm -rf build dist MANIFEST $(name).egg-info
	find . -type f -name \*.pyc -exec rm {} \;
	find . -d -type d -name __pycache__ -exec rm -rf {} \;
