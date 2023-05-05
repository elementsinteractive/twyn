import os

import pytest


@pytest.fixture
def requirements_txt_file(tmp_path):
    requirements_txt_file = tmp_path / "requirements.txt"
    requirements_txt_file.write_text(
        """
        South==1.0.1 --hash=sha256:abcdefghijklmno
        pycrypto>=2.6
        """
    )
    yield requirements_txt_file
    os.remove(requirements_txt_file)


@pytest.fixture
def poetry_lock_file(tmp_path):
    poetry_lock_file = tmp_path / "poetry.lock"
    poetry_lock_file.write_text(
        """
            [[package]]
            name = "charset-normalizer"
            version = "3.0.1"
            description = "The Real First Universal Charset Detector. Open, modern and \
                actively maintained alternative to Chardet."
            category = "main"
            optional = false
            python-versions = "*"

            [[package]]
            name = "flake8"
            version = "5.0.4"
            description = "the modular source code checker: pep8 pyflakes and co"
            category = "dev"
            optional = false
            python-versions = ">=3.6.1"

            [package.dependencies]
            mccabe = ">=0.7.0,<0.8.0"

            [[package]]
            name = "mccabe"
            version = "0.7.0"
            description = "McCabe checker, plugin for flake8"
            category = "dev"
            optional = false
            python-versions = ">=3.6"

            [metadata]
            lock-version = "1.1"
            python-versions = "^3.9"
            content-hash = "d518428f67ed390edb669028a3136be9a363472e206d4dec455af35381e"

            [metadata.files]
            charset-normalizer = []
            flake8 = []
            mccabe = []
        """
    )
    yield poetry_lock_file
    os.remove(poetry_lock_file)


@pytest.fixture
def pyproject_toml_file(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(
        """
    [tool.poetry.dependencies]
    python = "^3.11"
    requests = "^2.28.2"
    dparse = "^0.6.2"
    click = "^8.1.3"
    rich = "^13.3.1"
    rapidfuzz = "^2.13.7"
    regex = "^2022.10.31"
    
    [tool.poetry.scripts]
    twyn = "twyn.cli:entry_point"
    
    [tool.twyn]
    dependency_file="my_file.txt"
    selector_method="my_selector"
    logging_level="debug"
    allowlist=["boto4", "boto2"]

    """
    )
    yield pyproject_toml
    os.remove(pyproject_toml)
