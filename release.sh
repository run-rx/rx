#!/bin/bash

set -eux

[ "$#" -eq 1 ] || die "Version argument required, $# provided"

VERSION="${1}"

# TODO: check that venv is active.

# Update version.
sed -i '' "s/VERSION = '.*'/VERSION = '$VERSION'/" rx/client/configuration/local.py
sed -i '' 's/version = ".*"/version = "'$VERSION'"/' pyproject.toml

# Update README.md.
cp ../run-rx.github.io/index.md ./README.md

# Build.
poetry build

# Test.
python run_tests.py

# Deploy.
python -m twine upload "dist/run_rx-$VERSION*"
