import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def disable_click_echo():
    with mock.patch("click.echo"):
        yield


@contextmanager
def create_tmp_file(path: Path, data: str) -> Iterator[str]:
    path.write_text(data)
    yield str(path)
    os.remove(path)


@pytest.fixture
def requirements_txt_file(tmp_path: Path) -> Iterator[str]:
    requirements_txt_file = tmp_path / "requirements.txt"

    data = """
        South==1.0.1 --hash=sha256:abcdefghijklmno
        pycrypto>=2.6
        """

    with create_tmp_file(requirements_txt_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def poetry_lock_file_lt_1_5(tmp_path: Path) -> Iterator[str]:
    """Poetry lock version < 1.5."""
    poetry_lock_file = tmp_path / "poetry.lock"
    data = """
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
    with create_tmp_file(poetry_lock_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def poetry_lock_file_ge_1_5(tmp_path: Path) -> Iterator[str]:
    """Poetry lock version >= 1.5."""
    poetry_lock_file = tmp_path / "poetry.lock"
    data = """
            [[package]]
            name = "charset-normalizer"
            version = "3.0.1"
            description = "The Real First Universal Charset Detector. Open, modern and \
                actively maintained alternative to Chardet."
            optional = false
            python-versions = "*"

            [[package]]
            name = "flake8"
            version = "5.0.4"
            description = "the modular source code checker: pep8 pyflakes and co"
            optional = false
            python-versions = ">=3.6.1"

            [package.dependencies]
            mccabe = ">=0.7.0,<0.8.0"

            [[package]]
            name = "mccabe"
            version = "0.7.0"
            description = "McCabe checker, plugin for flake8"
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
    with create_tmp_file(poetry_lock_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def pyproject_toml_file(tmp_path: Path) -> Iterator[str]:
    pyproject_toml = tmp_path / "pyproject.toml"
    data = """
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
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file
