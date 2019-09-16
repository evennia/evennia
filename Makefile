default: install

BLACK_FORMAT_CONFIGS = --target-version py37 --line-length 100

install:
	python setup.py develop

fmt:
	black $(BLACK_FORMAT_CONFIGS) evennia

lint:
	black --check $(BLACK_FORMAT_CONFIGS) evennia
