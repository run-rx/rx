#!/bin/bash

set -eux

[ "$#" -eq 1 ] || die "Version argument required, $# provided"

VERSION="${1}"

# Update version.
sed -i '' "s/VERSION = '.*'/VERSION = '$VERSION'/" rx/client/configuration/local.py
sed -i '' 's/version = ".*"/version = "'$VERSION'"/' pyproject.toml

# Update README.md.
cp ../run-rx.github.io/index.md ./README.md

# Build.
poetry build

# Test.
PYTHONPATH=. pytest

# Deploy.
python -m twine upload "dist/run_rx-$VERSION*"
