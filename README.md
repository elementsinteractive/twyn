# Twyn

![Build Status](https://github.com/elementsinteractive/twyn/actions/workflows/test.yml/badge.svg)
[![PyPI version](https://img.shields.io/pypi/v/twyn)](https://pypi.org/project/twyn/)
[![Docker version](https://img.shields.io/docker/v/elementsinteractive/twyn?label=DockerHub&logo=docker&logoColor=f5f5f5)](https://hub.docker.com/r/elementsinteractive/twyn)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=yellow)](https://pypi.org/project/twyn/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/github/license/elementsinteractive/twyn)](LICENSE)

## Table of Contents

- [Overview](#overview)
- [Quickstart](#quickstart)
  - [Using `Twyn` as a cli tool](#using-twyn-as-a-cli-tool)
    - [Installation](#installation)
    - [Docker](#docker)
    - [Run](#run)
    - [JSON Format](#json-format)
  - [Using `Twyn` as a library](#using-twyn-as-a-library)
    - [Logging level](#logging-level)
- [Configuration](#configuration)
  - [Allowlist](#allowlist)
  - [Dependency files](#dependency-files)
  - [Check dependencies introduced through the CLI](#check-dependencies-introduced-through-the-cli)
  - [Selector method](#selector-method)
  - [Configuration file](#configuration-file)
  - [Cache](#cache)


## Overview
`Twyn` is a security tool that compares the name of your dependencies against a set of the most popular ones,
in order to determine if there is any similarity between them, preventing you from using a potentially illegitimate one.
In short, `Twyn` protects you against [typosquatting attacks](https://en.wikipedia.org/wiki/Typosquatting).

It works as follows:

1. Either choose to scan the dependencies in a dependencies file you specify (`--dependency-file`) or some dependencies introduced through the CLI (`--dependency`). If no option was provided, it will try to find a dependencies file in your working path.
2. If the name of your package name matches with the name of one of the most well known packages, the package is accepted.
3. If the name of your package is similar to the name of one of the most used packages, `Twyn` will prompt an error.
4. If your package name is not in the list of the most known ones and is not similar enough to any of those to be considered misspelled, the package is accepted. `Twyn` assumes that you're using either a not so popular package (therefore it can't verify its legitimacy) or a package created by yourself, therefore unknown for the rest.

## Quickstart

### Using twyn as a CLI tool
#### Installation

`Twyn` is available on PyPi repository, you can install it by running

```sh
pip install twyn[cli]
```

#### Docker

`Twyn` provides a Docker image, which can be found [here](https://hub.docker.com/r/elementsinteractive/twyn).

Use it like so:

```sh
docker pull elementsinteractive/twyn:latest
docker run elementsinteractive/twyn --help
```

#### Run

To run twyn simply type:

```sh
twyn run <OPTIONS>
```

For a list of all the available options as well as their expected arguments run:

```sh
twyn run --help
```

#### JSON format
If you want your output in JSON format, you can run `Twyn` with the following flag:

```python
  twyn run --json
```
This will output:

 ```json
  {"errors":[{"dependency":"reqests","similars":["requests","grequests"]}]}
 ```

### Using Twyn as a library


#### Installation
`Twyn` also supports being used as 3rd party library for you project. To install it, run:


```sh
pip install twyn
```

Example usage in your code:

```python
from twyn import check_dependencies

typos = check_dependencies()

for typo in typos.errors:
  print(f"Dependency:{typo.dependency}")
  print(f"Did you mean any of [{','.join(typo.similars)}]")
  
```

#### Logging level
By default, logging is disabled when running as a 3rd party library. To override this behaviour, you can:

```python
logging.basicConfig(level=logging.INFO)
logging.getLogger("twyn").setLevel(logging.INFO)
```

## Configuration

### Allowlist

It can happen that a legitimate package known by the user raises an error because it is too similar to one of the most trusted ones. Imagine that you are using internally a package that you developed called `reqests`. You can then add this packages to the `allowlist`, so it will not be reported as a typo:

```sh
twyn allowlist add <package>
```

To remove it simply:

```sh
twyn allowlist remove <package>
```

### Dependency files

To specify a dependency file through the command line run:

```sh
twyn run --dependency-file <file path>
```

The following dependency file formats are supported:

- `requirements.txt`
- `poetry.lock`
- `uv.lock`
- `package-lock.json` (v1, v2, v3)
- `yarn.lock` (v1, v2)

### Check dependencies introduced through the CLI

You can also check a dependency by entering it through the command line:

```sh
twyn run --dependency <dependency>
```

It does accept multiple dependencies at a time:

```sh
twyn run --dependency <dependency> --dependency <another_dependency>
```

When this option is selected, no dependency file is checked.

### Selector method

You can choose between different operational modes. These will determine which dependencies from the trusted set the analyzed dependency can be a typosquat of.

- `all`: Default option. It is the most exhaustive mode. It will check your package names against all the trusted ones without any assumption.
- `nearby-letter`: It will assume a typo on the first letter of the dependency is possible, but improbable if letters are farther apart in the keyboard. Specifically, it will compare the analyzed dependency against dependencies whose first letter is one step away in an `ANSI` keyboard layout.
- `first-letter`: It will assume a typo on the first letter is very improbable, and won't compare the analyzed dependency against dependencies with a different first letter.

> [!NOTE]
> Selecting an option is a matter of preference:  `all` is the slowest, but will have more false positives and less false negatives; while `first-letter` is the fastest, but it will have less false positives and more false negatives.

To select a specific operational mode through the CLI use the following command

```sh
twyn run --selector-method <method>
```

### Configuration file

You can save your configurations in a `.toml` file, so you don't need to specify them everytime you run `Twyn` in your terminal.

By default, it will try to find a `twyn.toml` file in your working directory when it's trying to load your configurations. If it does not find it, it will fallback to `pyproject.toml`.
However, you can specify a config file as follows:

```sh
twyn run --config <file>
```

All the configurations available through the command line are also supported in the config file.

```toml
[tool.twyn]
dependency_file="/my/path/requirements.txt"
selector_method="first_letter"
logging_level="debug"
allowlist=["my_package"]
source="https://mirror-with-trusted-dependencies.com/file.json"
```

The file format for each reference is as follows:

```jsonc
{
  "date": "string (ISO 8601 format, e.g. 2025-09-10T14:23:00+00)",
  "packages": [
    { "name": "string" }
  ]
}
```

### Cache
By default, `Twyn` will cache the list of trusted packages to a cache file, within the `.twyn` directory that will be automatically created. 

You can disable the cache by adding the following flag:

```python
  twyn run --no-cache
```
In which case it will download again the list of trusted packages, withou saving them to the cache file.

Cache file is valid for 30 days, after that period it will download again the trusted packages list.

To clear the cache, run:
```python
  twyn run cache clear
```


