#!/bin/bash
pylint --rcfile tests/pylint.conf $(git ls-files '*.py')
yamllint src/pyduin/data/boardfiles/ tests/data/boardfiles/ .github/workflows/

coverage run -m pytest tests/ -v
coverage report