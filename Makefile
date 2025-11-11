all: deps lint test

deps:
	@uv pip install -e ".[dev]"

ruff-format:
	@ruff format marshmallow_recipe tests

ruff-lint:
	@ruff check marshmallow_recipe tests

pyright:
	@pyright

lint: ruff-format ruff-lint pyright

test:
	@python3 -m pytest -vv --rootdir tests .

pyenv:
	echo marshmallow_recipe > .python-version && pyenv install -s 3.12 && pyenv virtualenv -f 3.12 marshmallow_recipe

pyenv-delete:
	pyenv virtualenv-delete -f marshmallow_recipe
