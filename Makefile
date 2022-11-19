# This is used with `make <option>` and is used for running various
# administration operations on the code.

TEST_GAME_DIR = .test_game_dir
TESTS ?= evennia

default:
	@echo " Usage: "
	@echo "  make install - install evennia (recommended to activate virtualenv first)"
	@echo "  make installextra - install evennia with extra-requirements (activate virtualenv first)"
	@echo "  make fmt/format - run the black autoformatter on the source code"
	@echo "  make lint - run black in --check mode"
	@echo "  make test - run evennia test suite with all default values."
	@echo "  make tests=evennia.path test - run only specific test or tests."
	@echo "  make testp - run test suite using multiple cores."
	@echo "  make publish - publish evennia to pypi (requires pypi credentials)

install:
	pip install -e .

installextra:
	pip install -e .
	pip install -e .[extra]

# black is configured from pyproject.toml
format:
	black evennia
	isort --profile black .

fmt: format

lint:
	black --check $(BLACK_FORMAT_CONFIGS) evennia

test:
	evennia --init $(TEST_GAME_DIR);\
	cd $(TEST_GAME_DIR);\
	evennia migrate;\
	evennia test --keepdb $(TESTS);\

testp:
	evennia --init $(TEST_GAME_DIR);\
	cd $(TEST_GAME_DIR);\
	evennia migrate;\
	evennia test --keepdb --parallel 4 $(TESTS);\

publish:
	rm -Rf dist/
	git clean -xdf	
	pip install --upgrade pip 
	pip install build twine 
	python -m build --sdist --wheel --outdir dist/ . 
	python -m twine upload dist/*
