#!/bin/bash
pylint --rcfile tests/pylint.conf "$(git ls-files '*.py')"
pytest tests/test_boardfile.py
yamllint src/pyduin/data/boardfiles/ tests/data/boardfiles/

