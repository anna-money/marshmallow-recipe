.PHONY: all uv rust deps lint test bench build build-wheel build-sdist

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
	@uv run maturin develop --release

lint: deps
	@uv run ruff format python/marshmallow_recipe tests
	@uv run ruff check python/marshmallow_recipe tests --fix
	@uv run pyright
	@cargo clippy

test: deps
	@uv run pytest -vv $(or $(T),.)

bench: deps
	@uv run python benchmarks/bench_serialization.py

build: deps
	@uv run maturin build --release

build-wheel: deps
	@uv run maturin build --release --out dist

build-sdist: deps
	@uv run maturin sdist --out dist
