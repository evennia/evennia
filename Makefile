# This is used with `make <option>` and is used for running various
# administration operations on the code.

BLACK_FORMAT_CONFIGS = --target-version py37 --line-length 100
TEST_GAME_DIR = .test_game_dir
tests?=evennia

default:
	@echo " Usage: "
	@echo "  make install - install evennia (recommended to activate virtualenv first)"
	@echo "  make fmt/format - run the black autoformatter on the source code"
	@echo "  make lint - run black in --check mode"
	@echo "  make test - run evennia test suite with all default values."
	@echo "  make tests=evennia.path test - run only specific test or tests."
	@echo "  make testp - run test suite using multiple cores."

install:
	pip install -e .

format:
	black $(BLACK_FORMAT_CONFIGS) evennia

fmt: format

lint:
	black --check $(BLACK_FORMAT_CONFIGS) evennia

test:
	evennia --init $(TEST_GAME_DIR);\
	cd $(TEST_GAME_DIR);\
	evennia migrate;\
	evennia test --keepdb $(tests);\

testp:
	evennia --init $(TEST_GAME_DIR);\
	cd $(TEST_GAME_DIR);\
	evennia migrate;\
	evennia test --keepdb --parallel 4 $(tests);\
