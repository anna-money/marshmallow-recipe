all: deps lint test

uv:
	@which uv >/dev/null 2>&1 || { \
		echo "uv is not installed"; \
		exit 1;\
	}

build-rust:
	@cd packages/marshmallow-recipe-speedup && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 uv run maturin develop --release

deps: uv
	@uv sync --extra dev
	@$(MAKE) build-rust

lint: deps
	@uv run ruff format marshmallow_recipe tests
	@uv run ruff check marshmallow_recipe tests --fix
	@uv run pyright

test: build-rust
	@uv run pytest -vv .
