.PHONY: all uv rust deps lint test test-release build build-wheel build-sdist

all: deps lint test

uv:
	@which uv >/dev/null 2>&1 || { \
		echo "uv is not installed"; \
		exit 1;\
	}

rust:
	@which cargo >/dev/null 2>&1 || { \
		echo "Rust is not installed"; \
		exit 1;\
	}

deps: uv rust
	@uv sync --extra dev
	@cd packages/marshmallow-recipe-speedup && uv run maturin develop --release

lint: deps
	@uv run ruff format marshmallow_recipe tests
	@uv run ruff check marshmallow_recipe tests --fix
	@uv run pyright

test: deps
	@uv run pytest -vv $(or $(T),.)

build: uv
	@uv build

build-wheel: deps
	@cd packages/marshmallow-recipe-speedup && uv run maturin build --release --out dist

build-sdist: deps
	@cd packages/marshmallow-recipe-speedup && uv run maturin sdist --out dist

test-release: uv rust
	@uv sync --extra dev --no-install-package marshmallow-recipe-speedup
	@cd packages/marshmallow-recipe-speedup && uv run maturin build --release --out dist
	@WHEEL=$$(ls packages/marshmallow-recipe-speedup/dist/*.whl) && uv run --with "$$WHEEL" pytest -vv .
