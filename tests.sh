#!/bin/bash
pylint --rcfile tests/pylint.conf $(git ls-files '*.py')
