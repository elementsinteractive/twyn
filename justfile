# VARIABLE DEFINITIONS
venv := ".venv"
bin := venv + "/bin"
python := bin + "/python"
python_version := "python3.11"
target_dirs := "src tests"


# SENTINELS
venv-exists := path_exists(venv)

# ALIASES
alias t := test


# RECIPES

# Shows list of recipes.
help:
    just --list --unsorted

# Generate the virtual environment.
venv:
    @if ! {{ venv-exists }}; \
    then \
    POETRY_VIRTUALENVS_IN_PROJECT=1 poetry env use {{ python_version }}; \
    poetry install; \
    fi

# Cleans all artifacts generated while running this project, including the virtualenv.
clean:
    @rm -f .coverage*
    @rm -rf {{ venv }}

# Runs the tests with the specified arguments (any path or pytest argument).
test *test-args='': venv
    poetry run pytest {{ test-args }} --no-cov

# Runs all tests including coverage report.
test-all: venv
    poetry run pytest

# Format all code in the project.
format: venv
    poetry run ruff {{ target_dirs }} --fix

# Lint all code in the project.
lint: venv
    poetry run ruff check {{ target_dirs }}
    poetry run mypy {{ target_dirs }}
