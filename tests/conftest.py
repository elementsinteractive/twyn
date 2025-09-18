import datetime
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest import mock

import pytest


@contextmanager
def create_tmp_file(path: Path, data: str) -> Iterator[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    yield path


@contextmanager
def patch_pypi_packages_download(packages: list[str]) -> Iterator[mock.Mock]:
    """Patcher of `requests.get` for Top PyPi list.

    Replaces call with the output you would get from downloading the top PyPi packages list.
    """
    json_response = {"packages": packages, "date": datetime.datetime.now().isoformat()}
    with mock.patch("twyn.trusted_packages.TopPyPiReference._download") as mock_download:
        mock_download.return_value = json_response
        yield mock_download


@contextmanager
def patch_npm_packages_download(packages: list[str]) -> Iterator[mock.Mock]:
    """Patcher of `requests.get` for Top Npm list.

    Replaces call with the output you would get from downloading the top Npm packages list.
    """
    json_response = {"packages": packages, "date": datetime.datetime.now().isoformat()}

    with mock.patch("twyn.trusted_packages.TopNpmReference._download") as mock_download:
        mock_download.return_value = json_response
        yield mock_download


@pytest.fixture
def requirements_txt_file(tmp_path: Path) -> Iterator[Path]:
    requirements_txt_file = tmp_path / "requirements.txt"

    data = """
        South==1.0.1 --hash=sha256:abcdefghijklmno
        pycrypto>=2.6
        requests~=2.25.1
        django[postgres]>=3.2
        -e git+https://github.com/psf/requests.git#egg=requests
        https://github.com/psf/requests3.git#egg=urllib3
        Flask; python_version<'3.8'
        """

    with create_tmp_file(requirements_txt_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def poetry_lock_file_lt_1_5(tmp_path: Path) -> Iterator[Path]:
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
def poetry_lock_file_ge_1_5(tmp_path: Path) -> Iterator[Path]:
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
def uv_lock_file(tmp_path: Path) -> Iterator[Path]:
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
def uv_lock_file_with_typo(tmp_path: Path) -> Iterator[Path]:
    """Uv lock file with a typo."""
    uv_lock_file = tmp_path / "uv.lock"
    data = """
            version = 1
            revision = 2
            requires-python = ">=3.13, <4"

            [[package]]
            name = "reqests"


            [[package]]
            name = "anyio"


            [[package]]
            name = "argcomplete"


        """
    with create_tmp_file(uv_lock_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def pyproject_toml_file(tmp_path: Path) -> Iterator[Path]:
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
    dependency_file=["my_file.txt", "my_other_file.txt"]
    selector_method="all"
    logging_level="debug"
    allowlist=["boto4", "boto2"]
    use_cache=false
    """
    with create_tmp_file(pyproject_toml, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def package_lock_json_file_v2(tmp_path: Path) -> Iterator[Path]:
    """NPM package-lock.json file."""
    package_lock_file = tmp_path / "package-lock.json"
    data = """{
        "name": "test-project",
        "version": "1.0.0",
        "lockfileVersion": 2,
        "requires": true,
        "packages": {
            "": {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {
                "express": "4.18.2"
            }
            },
            "node_modules/express": {
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
            "integrity": "sha512-express",
            "dependencies": {
                "body-parser": "1.20.1"
            }
            },
            "node_modules/body-parser": {
            "version": "1.20.1",
            "resolved": "https://registry.npmjs.org/body-parser/-/body-parser-1.20.1.tgz",
            "integrity": "sha512-bodyparser",
            "dependencies": {
                "debug": "2.6.9"
            }
            },
            "node_modules/debug": {
            "version": "2.6.9",
            "resolved": "https://registry.npmjs.org/debug/-/debug-2.6.9.tgz",
            "integrity": "sha512-debug"
            }
        },
        "dependencies": {
            "express": {
            "version": "4.18.2",
            "requires": {
                "body-parser": "1.20.1"
            },
            "dependencies": {
                "body-parser": {
                "version": "1.20.1",
                "requires": {
                    "debug": "2.6.9"
                }
                }
            }
            }
        }
        }
        """
    with create_tmp_file(package_lock_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def package_lock_json_file_v1(tmp_path: Path) -> Iterator[Path]:
    """NPM package-lock.json v1 file."""
    package_lock_file = tmp_path / "package-lock.json"
    data = """{
        "name": "test-project",
        "version": "1.0.0",
        "lockfileVersion": 1,
        "requires": true,
        "dependencies": {
            "express": {
                "version": "4.18.2",
                "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
                "integrity": "sha512-express",
                "requires": { "body-parser": "1.20.1" },
                "dependencies": {
                    "body-parser": {
                        "version": "1.20.1",
                        "resolved": "https://registry.npmjs.org/body-parser/-/body-parser-1.20.1.tgz",
                        "integrity": "sha512-bodyparser",
                        "requires": { "debug": "2.6.9" },
                        "dependencies": {
                            "debug": {
                                "version": "2.6.9",
                                "resolved": "https://registry.npmjs.org/debug/-/debug-2.6.9.tgz",
                                "integrity": "sha512-debug"
                            }
                        }
                    }
                }
            }
        }
    }"""
    with create_tmp_file(package_lock_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def package_lock_json_file_v3(tmp_path: Path) -> Iterator[Path]:
    """NPM package-lock.json v3 file."""
    package_lock_file = tmp_path / "package-lock.json"
    data = """{
        "name": "test-project",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "requires": true,
        "packages": {
            "": {
                "name": "test-project",
                "version": "1.0.0",
                "dependencies": {
                    "express": "4.18.2"
                }
            },
            "node_modules/express": {
                "version": "4.18.2",
                "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
                "integrity": "sha512-express",
                "dependencies": {
                    "body-parser": "1.20.1"
                }
            },
            "node_modules/body-parser": {
                "version": "1.20.1",
                "resolved": "https://registry.npmjs.org/body-parser/-/body-parser-1.20.1.tgz",
                "integrity": "sha512-bodyparser",
                "dependencies": {
                    "debug": "2.6.9"
                }
            },
            "node_modules/debug": {
                "version": "2.6.9",
                "resolved": "https://registry.npmjs.org/debug/-/debug-2.6.9.tgz",
                "integrity": "sha512-debug"
            }
        }
    }"""
    with create_tmp_file(package_lock_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def yarn_lock_file_v1(tmp_path: Path) -> Iterator[Path]:
    yarn_file = tmp_path / "yarn.lock"
    data = """# THIS IS AN AUTOGENERATED FILE. DO NOT EDIT THIS FILE DIRECTLY.
# yarn lockfile v1
lodash@^4.17.21:
version "4.17.21"
resolved "https://registry.yarnpkg.com/lodash/-/lodash-4.17.21.tgz#abcdef1234567890"
integrity sha512-xxxxxxx

react@^18.2.0:
version "18.2.0"
resolved "https://registry.yarnpkg.com/react/-/react-18.2.0.tgz#abcdef1234567890"
integrity sha512-yyyyyyy
dependencies:
    loose-envify "^1.1.0"

react-dom@^18.2.0:
version "18.2.0"
resolved "https://registry.yarnpkg.com/react-dom/-/react-dom-18.2.0.tgz#abcdef1234567890"
integrity sha512-zzzzzzz
dependencies:
    loose-envify "^1.1.0"
    react "^18.2.0"
"@babel/helper-plugin-utils@^7.0.0", "@babel/helper-plugin-utils@^7.10.4", "@babel/helper-plugin-utils@^7.12.13", "@babel/helper-plugin-utils@^7.14.5", "@babel/helper-plugin-utils@^7.25.9", "@babel/helper-plugin-utils@^7.8.0":
  version "7.26.5"
  resolved "https://registry.npmmirror.com/@babel/helper-plugin-utils/-/helper-plugin-utils-7.26.5.tgz#18580d00c9934117ad719392c4f6585c9333cc35"
  integrity sha512-RS+jZcRdZdRFzMyr+wcsaqOmld1/EqTghfaBGQQd/WnRdzdlvSZ//kF7U8VQTxf1ynZ4cjUcYgjVGx13ewNPMg==
    """
    with create_tmp_file(yarn_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture
def yarn_lock_file_v2(tmp_path: Path) -> Iterator[Path]:
    yarn_file = tmp_path / "yarn.lock"
    data = """
        __metadata:
        version: 4
        cacheKey: 8

        "react@npm:^17.0.2":
        version: 17.0.2
        resolution: "react@npm:17.0.2"
        dependencies:
            loose-envify: ^1.1.0

        "react-dom@npm:^17.0.2":
        version: 17.0.2
        resolution: "react-dom@npm:17.0.2"
        dependencies:
            react: ^17.0.2
            scheduler: ^0.20.2

        "lodash@npm:^4.17.21":
        version: 4.17.21
        resolution: "lodash@npm:4.17.21"

        """
    with create_tmp_file(yarn_file, data) as tmp_file:
        yield tmp_file


@pytest.fixture(autouse=True)
def fail_on_requests_get(request) -> Generator[None, Any, None]:
    with mock.patch("requests.get") as m_get:
        m_get.side_effect = RuntimeError("`requests.get()` was called!")
        yield
