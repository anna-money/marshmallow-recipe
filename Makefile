all: deps lint test

deps:
	@python3 -m pip install --upgrade pip && pip3 install -r requirements-dev.txt

black:
	@black --line-length 120 marshmallow_recipe tests

isort:
	@isort --line-length 120 --use-parentheses --multi-line 3 --combine-as --trailing-comma marshmallow_recipe tests

flake8:
	@flake8 --max-line-length 120 --ignore C901,C812,E203 --extend-ignore W503 marshmallow_recipe tests

mypy:
	@mypy --ignore-missing-imports marshmallow_recipe tests

lint: black isort flake8 mypy

test:
	@python3 -m pytest -vv --rootdir tests .

pyenv:
	echo marshmallow_recipe > .python-version && pyenv install -s 3.11 && pyenv virtualenv -f 3.11 marshmallow_recipe

pyenv-delete:
	pyenv virtualenv-delete -f marshmallow_recipe
