# VARIABLE DEFINITIONS
venv := ".venv"
python_version :="3.13"
run := "uv run"

venv-exists := path_exists(venv)

target_dirs := "src tests dependencies"

# ALIASES
alias t := test
help:
    just --list --unsorted

# Create a new venv with all the dependencies groups
venv: 
    @if ! {{ venv-exists }}; \
    then \
    uv sync --frozen --all-extras --all-groups; \
    fi

# Cleans all artifacts generated while running this project, including the virtualenv.
clean: 
    @rm -f .coverage*
    @rm -rf {{ venv }}
    @rm -rf dist/
    @rm -rf .mypy_cache/
    @rm -rf .ruff_cache/
    @rm -rf .pytest_cache/
    @find . -type d -name '__pycache__' -exec rm -r {} +


# Runs the tests with the specified arguments (any path or pytest argument).
test *test-args='': venv
    {{ run }}  pytest {{ test-args }} --no-cov 


# Format all code in the project.
format:  venv
    {{ run }} ruff format {{ target_dirs }}
    {{ run }} ruff check {{ target_dirs }} --fix

# Lint all code in the project.
lint: venv
    {{ run }} ruff format --check {{ target_dirs }}
    {{ run }} ruff check {{ target_dirs }}
    {{ run }} mypy {{ target_dirs }}

# Build the package using hatchling
build: venv
    {{ run }} build

# Install package in development mode
install-dev: venv
    uv pip install -e .

download ecosystem: venv
    uv run --no-project dependencies/scripts/download_packages.py download {{ecosystem}}