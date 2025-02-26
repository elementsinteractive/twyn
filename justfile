# VARIABLE DEFINITIONS
venv := ".venv"
python_version :="3.13"
target_dirs := "src tests"

# ALIASES
alias t := test


# RECIPES

# Shows list of recipes.
help:
    just --list --unsorted

# Cleans all artifacts generated while running this project, including the virtualenv.
venv: 
    @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv sync

# Cleans all artifacts generated while running this project, including the virtualenv.
clean:
    @rm -f .coverage*
    @rm -rf {{ venv }}

# Runs the tests with the specified arguments (any path or pytest argument).
test *test-args='': 
    @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv run pytest {{ test-args }} --no-cov 

# Runs all tests including coverage report.
test-all: 
    @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv run pytest

# Format all code in the project.
format:  
    @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv run ruff check {{ target_dirs }} --fix

# Lint all code in the project.
lint: 
    @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv run ruff check {{ target_dirs }}
    @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv run mypy {{ target_dirs }}


# Generate requirements.txt file
dependencies:
        @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv sync
        @UV_PROJECT_ENVIRONMENT={{ venv }} UV_PYTHON={{ python_version }} uv pip freeze > requirements.txt
        
