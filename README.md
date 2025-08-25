# Twyn

![Build Status](https://github.com/elementsinteractive/twyn/actions/workflows/test.yml/badge.svg)
[![PyPI version](https://img.shields.io/pypi/v/twyn)](https://pypi.org/project/twyn/)
[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=yellow)](https://pypi.org/project/twyn/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/github/license/elementsinteractive/twyn)](LICENSE)

![](https://github.com/elementsinteractive/twyn/blob/main/assets/twyn.gif)

## Table of Contents

- [Overview](#overview)
- [Quickstart](#quickstart)
  - [Installation](#installation)
  - [Docker](#docker)
  - [Run](#run)
- [Configuration](#configuration)
  - [Allowlist](#allowlist)
  - [Dependency files](#dependency-files)
  - [Check dependencies introduced through the CLI](#check-dependencies-introduced-through-the-cli)
  - [Selector method](#selector-method)
  - [Configuration file](#configuration-file)

## Overview
Twyn is a security tool that compares the name of your dependencies against a set of the most popular ones,
in order to determine if there is any similarity between them, preventing you from using a potentially illegitimate one.
In short, Twyn protects you against [typosquatting attacks](https://en.wikipedia.org/wiki/Typosquatting).

It works as follows:

1. Either choose to scan the dependencies in a dependencies file you specify (`--dependency-file`) or some dependencies introduced through the CLI (`--dependency`). If no option was provided, it will try to find a dependencies file in your working path.
2. If the name of your package name matches with the name of one of the most well known packages, the package is accepted.
3. If the name of your package is similar to the name of one of the most used packages, Twyn will prompt an error.
4. If your package name is not in the list of the most known ones and is not similar enough to any of those to be considered misspelled, the package is accepted. Twyn assumes that you're using either a not so popular package (therefore it can't verify its legitimacy) or a package created by yourself, therefore unknown for the rest.

## Quickstart

### Installation

Twyn is available on PyPi repository, you can install it by running

```sh
pip install twyn
```

### Docker

Twyn provides a Docker image, which can be found [here](https://hub.docker.com/r/elementsinteractive/twyn).

Use it like so:

```sh
docker pull elementsinteractive/twyn:latest
docker run elementsinteractive/twyn --help
```

### Run

To run twyn simply type:

```sh
twyn run <OPTIONS>
```

For a list of all the available options as well as their expected arguments run:

```sh
twyn run --help
```

## Configuration

### Allowlist

It can happen that a legitimate package known by the user raises an error because is too similar to one of the most trusted ones.
You can then add this packages to the `allowlist`, so it will be skipped:

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

You can save your configurations in a `.toml` file, so you don't need to specify them everytime you run Twyn in your terminal.

By default, it will try to find a `pyproject.toml` file in your working directory when it's trying to load your configurations.
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
pypi_reference="https://mirror-with-trusted-dependencies.com/file.json"
```

> [!WARNING]
> `twyn` will have a default reference URL for every source of trusted packages that is configurable.
> If you want to protect yourself against spoofing attacks, it is recommended to set your own
> reference url.

The file format for each reference is as follows:

- **PyPI reference**:

```ts
{
    rows: {project: string}[]
}
```

### Cache
By default, Twyn will cache the list of trusted packages to a cache file (.twyn/trusted_packages.json). 

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