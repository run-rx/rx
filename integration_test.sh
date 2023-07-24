#!/bin/bash

set -eux

TEST_RXROOT=sample_rxroot

rm -rf "${TEST_RXROOT}"
mkdir "${TEST_RXROOT}"

nrx() {
  # TODO: add dev/prod flag.
  python -m rx --rxroot="$(pwd)/${TEST_RXROOT}" $@
}

# Init
nrx init --quiet
nrx ls

# Try writing files locally and remotely
nrx touch bar
touch baz

# Check files were written
nrx ls
nrx ls rx-out
