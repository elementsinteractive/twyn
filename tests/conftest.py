from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest


@contextmanager
def create_tmp_file(path: Path, data: str) -> Iterator[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    yield str(path)


@contextmanager
def patch_pypi_packages_download(packages: Iterable[str]) -> Iterator[mock.Mock]:
    """Patcher of `requests.get` for Top PyPi list.

    Replaces call with the output you would get from downloading the top PyPi packages list.
    """
    json_response = {"rows": [{"project": name} for name in packages]}

    with mock.patch("twyn.trusted_packages.references.TopPyPiReference._download") as mock_download:
        mock_download.return_value = json_response

        yield mock_download


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
def uv_lock_file(tmp_path: Path) -> Iterator[str]:
    """Uv lock file."""
    uv_lock_file = tmp_path / "uv.lock"
    data = """
            version = 1
            revision = 2
            requires-python = ">=3.13, <4"

            [[package]]
            name = "annotated-types"
            version = "0.7.0"
            source = { registry = "https://pypi.org/simple" }
            sdist = { url = "https://files.pythonhosted.org/packages/ee/67/531ea369ba64dcff5ec9c3402f9f51bf748cec26dde048a2f973a4eea7f5/annotated_types-0.7.0.tar.gz", hash = "sha256:aff07c09a53a08bc8cfccb9c85b05f1aa9a2a6f23728d790723543408344ce89", size = 16081, upload-time = "2024-05-20T21:33:25.928Z" }
            wheels = [
                { url = "https://files.pythonhosted.org/packages/78/b6/6307fbef88d9b5ee7421e68d78a9f162e0da4900bc5f5793f6d3d0e34fb8/annotated_types-0.7.0-py3-none-any.whl", hash = "sha256:1f02e8b43a8fbbc3f3e0d4f0f4bfc8131bcb4eebe8849b8e5c773f3a1c582a53", size = 13643, upload-time = "2024-05-20T21:33:24.1Z" },
            ]

            [[package]]
            name = "anyio"
            version = "4.9.0"
            source = { registry = "https://pypi.org/simple" }
            dependencies = [
                { name = "idna" },
                { name = "sniffio" },
            ]
            sdist = { url = "https://files.pythonhosted.org/packages/95/7d/4c1bd541d4dffa1b52bd83fb8527089e097a106fc90b467a7313b105f840/anyio-4.9.0.tar.gz", hash = "sha256:673c0c244e15788651a4ff38710fea9675823028a6f08a5eda409e0c9840a028", size = 190949, upload-time = "2025-03-17T00:02:54.77Z" }
            wheels = [
                { url = "https://files.pythonhosted.org/packages/a1/ee/48ca1a7c89ffec8b6a0c5d02b89c305671d5ffd8d3c94acf8b8c408575bb/anyio-4.9.0-py3-none-any.whl", hash = "sha256:9f76d541cad6e36af7beb62e978876f3b41e3e04f2c1fbf0884604c0a9c4d93c", size = 100916, upload-time = "2025-03-17T00:02:52.713Z" },
            ]

            [[package]]
            name = "argcomplete"
            version = "3.6.2"
            source = { registry = "https://pypi.org/simple" }
            sdist = { url = "https://files.pythonhosted.org/packages/16/0f/861e168fc813c56a78b35f3c30d91c6757d1fd185af1110f1aec784b35d0/argcomplete-3.6.2.tar.gz", hash = "sha256:d0519b1bc867f5f4f4713c41ad0aba73a4a5f007449716b16f385f2166dc6adf", size = 73403, upload-time = "2025-04-03T04:57:03.52Z" }
            wheels = [
                { url = "https://files.pythonhosted.org/packages/31/da/e42d7a9d8dd33fa775f467e4028a47936da2f01e4b0e561f9ba0d74cb0ca/argcomplete-3.6.2-py3-none-any.whl", hash = "sha256:65b3133a29ad53fb42c48cf5114752c7ab66c1c38544fdf6460f450c09b42591", size = 43708, upload-time = "2025-04-03T04:57:01.591Z" },
            ]

        """
    with create_tmp_file(uv_lock_file, data) as tmp_file:
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
    selector_method="all"
    logging_level="debug"
    allowlist=["boto4", "boto2"]

    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file
