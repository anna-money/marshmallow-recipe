all: deps lint test

UV_EXTRA_ARGS ?=

uv:
	@which uv >/dev/null 2>&1 || { \
		echo "uv is not installed"; \
		exit 1;\
	}

deps: uv
	@uv sync --all-extras

ruff-format:
	@uv run $(UV_EXTRA_ARGS) ruff format marshmallow_recipe tests

ruff-lint:
	@uv run $(UV_EXTRA_ARGS) ruff check marshmallow_recipe tests --fix

pyright:
	@uv run $(UV_EXTRA_ARGS) pyright

lint: ruff-format ruff-lint pyright

test:
	@uv run $(UV_EXTRA_ARGS) pytest -vv --rootdir tests .
