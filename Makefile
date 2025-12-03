all: deps lint test

uv:
	@which uv >/dev/null 2>&1 || { \
		echo "uv is not installed"; \
		exit 1;\
	}

deps: uv
	@uv sync --all-extras

ruff-format:
	@uv run ruff format marshmallow_recipe tests

ruff-lint:
	@uv run ruff check marshmallow_recipe tests --fix

pyright:
	@uv run pyright

lint: ruff-format ruff-lint pyright

test:
	@uv run pytest -vv --rootdir tests .
