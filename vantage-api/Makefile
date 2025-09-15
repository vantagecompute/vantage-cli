SHELL:=/bin/bash
ROOT_DIR:=$(shell dirname $(shell pwd))
PACKAGE_NAME:=api

.PHONY: install
install: ## Install the project's dependencies
	poetry install

.PHONY: test
test: install ## Run the unit tests
	poetry run pytest

.PHONY: lint
lint: install ## Lint the project using black, isort and flake8
	poetry run ruff check ${PACKAGE_NAME} tests scripts cloud_account_stack --fix

.PHONY: qa
qa: lint test ## Run the quality assurance check
	echo "All tests pass! Ready for deployment"

.PHONY: format
format: install ## Format the code using black and isort
	poetry run ruff format ${PACKAGE_NAME} tests scripts alembic/versions cloud_account_stack

.PHONY: local-dev
local-dev: ## Run a local dev server
	docker-compose build api migration
	docker-compose up --build api

.PHONY: clean
clean: ## Clean all files/folders created by the project
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete
	@find . -iname '.zip' -delete
	@find . -iname 'test-reports' -delete
	@rm -r .pytest_cache

.PHONY: help
help: ## Print the targets and their descriptions
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'