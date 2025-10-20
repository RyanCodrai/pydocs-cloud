# Local development configuration
CONTAINER_NAME?=fastapi-dev

# The .PHONY rule is used to declare that 'test' and 'tests' are not files but rather commands.
# This prevents Make from checking for the existence of a file named 'test' or 'tests' and
# ensures that the recipes for these targets are always executed when requested.
.PHONY: test tests

build: ## Build image
	docker-compose -f docker-compose.dev.yaml build

deps: ## Update and lock dependencies
	@if [ "$(IGNORE_DOCKER)" != "1" ] && ! [ -f /.dockerenv ]; then \
		echo "Error: Dependencies must be managed inside the Docker container."; \
		echo "Use 'make start' to start the container"; \
		exit 1; \
	fi
	uv lock --upgrade

start:
	@if [ -f /.dockerenv ]; then \
		echo "You are already inside the container :)"; \
	else \
		docker-compose -f docker-compose.dev.yaml up -d --build; \
		docker exec -it $(CONTAINER_NAME) bash; \
	fi

stop:
	docker-compose -f docker-compose.dev.yaml down

restart: stop start

app:
	uvicorn --host 0.0.0.0 --port 8080 src.main:application --reload

deploy-local: ## Full local deployment: compile deps, build, and start
	@echo "Starting full local deployment..."
	@if [ ! -f /.dockerenv ]; then \
		echo "Starting container to compile dependencies..."; \
		docker-compose -f docker-compose.dev.yaml up -d; \
		echo "Compiling dependencies inside container..."; \
		docker exec -it $(CONTAINER_NAME) make deps IGNORE_DOCKER=1; \
		echo "Final build and start..."; \
		docker-compose -f docker-compose.dev.yaml up -d --build; \
		echo "Starting FastAPI application..."; \
		docker exec -it $(CONTAINER_NAME) make app; \
	else \
		echo "You are already inside the container. Run 'make deps && exit' then 'make build && make start'"; \
	fi

tests:
	@if [ "$(IGNORE_DOCKER)" != "1" ] && ! [ -f /.dockerenv ]; then \
		echo "Error: Tests must be run inside the Docker container."; \
		echo "Use 'make start' to start the container"; \
		exit 1; \
	fi
	coverage run -m pytest $(TEST_PATH) --log-cli-level=INFO && coverage report

unit-tests: ## Run unit tests
	@$(MAKE) tests TEST_PATH=tests/unit

recreate-db: ## Recreate the PostgreSQL database container and volume
	docker stop postgres_db || true
	docker rm postgres_db || true
	docker volume rm dojo-user_postgres_data || true
	docker-compose -f docker-compose.dev.yaml up -d db
	@echo "PostgreSQL container and volume have been recreated."


help:
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)