#!/bin/bash
#
# To build the client release, run:
#
#   $ rx package/build.sh
#

set -eux

apt-get update
# Install aclocal, make
# zip needed for packaging step.
apt-get install -y automake build-essential git liblz4-dev gcc g++ gawk \
  autoconf automake python3-cmarkgfm libacl1-dev libattr1-dev libzstd-dev \
  libssl-dev libxxhash-dev zip

# Working dir.
cd rx-out

git clone https://github.com/WayneD/rsync.git
cd rsync
# Ridiculously, this rsync requires commonmark to installed for documentation.
python3 -m pip install commonmark
./configure LDFLAGS="/usr/local/lib/libxxhash.a"
make

# Back to rxroot.
cd ../../

pyinstaller rx/client/commands/exec.py \
  --add-binary rx-out/rsync/rsync:bin \
  --add-data install:install \
  --paths=. \
  --name rx \
  --onefile
