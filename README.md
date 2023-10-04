# Twyn

![Build Status](https://github.com/elementsinteractive/twyn/actions/workflows/test.yml/badge.svg)
[![PyPI version](https://img.shields.io/pypi/v/twyn)](https://pypi.org/project/twyn/)
[![Python Version](https://img.shields.io/pypi/pyversions/twyn?logo=python&logoColor=yellow)](https://pypi.org/project/twyn/)
![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)
[![License](https://img.shields.io/github/license/elementsinteractive/twyn)](LICENSE)


![](https://github.com/elementsinteractive/twyn/blob/main/assets/twyn.gif)

Twyn is a security tool that compares the name of your dependencies against a set of the most popular ones, 
in order to determine if there is any similarity between them, preventing you from using a potentially illegitimate one.
In short, Twyn protects you against [typosquatting attacks](https://en.wikipedia.org/wiki/Typosquatting).

It works as follows:

1. It will try to find a dependencies file in your working path. You can freely specify a different path for that file.
2. If your installed package name matches with the name of one of the most well known packages, the package is accepted.
3. If the name of your package is similar to the name one of the most used packages, Twyn will prompt an error.
4. If your package name is not in the list of the most known ones and is not similar enough to any of those to be considered misspelled, the package is accepted. Twyn assumes that you're using either a not so popular package (therefore it can't verify its legitimacy) or a package created by yourself, therefore unknown for the rest.

## Docker
Twyn provides a Docker image, which can be found [here](https://hub.docker.com/r/elementsinteractive/twyn).

## Quickstart
### Installation
Twyn is available on PyPi repository, you can install it by running
    
    pip install twyn

### Run
To run twyn simply type:

    twyn run <OPTIONS>

For a list of all the available options as well as their expected arguments run:

    twyn run --help


## Configuration

### Allowlist
It can happen that a legitimate package known by the user raises an error because is too similar to one of the most trusted ones.
You can then add this packages to the `allowlist`, so it will be skipped:

    twyn allowlist add <package>

To remove it simply:

    twyn allowlist remove <package>

### Dependency files
To specify a dependency file through the command line run:

    twyn run --dependency-file <file path>

Currently it supports these dependency file formats.
- `requirements.txt`
- `poetry.lock`

### Selector method
You can choose between different operational modes:
- `all`: Default option. It is the most exhaustive mode. It will check your package names against the trusted ones without any assumption.
- `nearby-letter`: will consider a possible typo in the first letter of your package name, so it will also consider all the nearby characters (in an English keyboard) when computing the distance between words.
- `first-letter`: will assume the first letter of your package is correct. It is the fastest mode but the least reliable one.

To select a specific operational mode through the CLI use the following command

    twyn run --selector-method <method>

### Configuration file
You can save your configurations in a `.toml` file, so you don't need to specify them everytime you run Twyn in your terminal.

By default, it will try to find a `pyproject.toml` file in your working directory when it's trying to load your configurations.
However, you can specify a config file as follows:
    
    twyn run --config <file>

All the configurations available through the command line are also supported in the config file. 

    [tool.twyn]
    dependency_file="/my/path/requirements.txt"
    selector_method="first_letter"
    logging_level="debug"
    allowlist=["my_package"]