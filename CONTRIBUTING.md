# Contributing to Twyn
Welcome to Twyn! Thanks for contributing to the project 🎉

Feel free to pick up any of the issues that are already created. If you are a first time contributor, you can start with any of the items labeled as `good first issue`
For new feature proposals, please create first an issue to start a discussion about it.

## How to contribute
1. Create a fork of the main [Twyn repository](https://github.com/elementsinteractive/twyn)
2. Clone it from GitHub

        git clone git@github.com:<username>/twyn.git
        cd twyn/
3. Make sure to have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed in your system, as well as [just](https://github.com/casey/just).
4. Set up your working environment: create a virtual environment and install the project dependencies. 
The following command will do both:
    
        just venv
5. Create tests for your changes. We recommend you to follow a 
[Test Driven Development (TDD)](https://en.wikipedia.org/wiki/Test-driven_development) approach when creating both the tests and the code.
6. Run all the tests to ensure everything is fine

         just test
7. After adding the changes, update the Readme.md file if needed. You don't need to update the CHANGELOG.md file nor the version, as it will be done automatically after merging.
8. Make sure to follow [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) standards so the version is updated correctly.
9. Submit your PR :) 

