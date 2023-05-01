#!/bin/bash
#
# To build the client release, create .rx/remotes/oldbuntu containing:
#
#   {
#     "image": {
#        "docker": "ubuntu:20.04"
#     }
#   }
#
# Then run:
#
#   $ rx init --remote=oldbuntu
#   $ rx package/ubuntu.sh
#

set -eux

# Remove _apt from /etc/passwd.
sed '/_apt/d' /etc/passwd > passwd.tmp
mv passwd.tmp /etc/passwd

# Set up timezone data for pkg-config install.
export DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true
cat <<EOF > tzdata
tzdata tzdata/Areas select US
tzdata tzdata/Zones/US select Eastern
EOF
debconf-set-selections tzdata
rm tzdata

# apt-get update
apt-get install -y autoconf automake build-essential git liblz4-dev gcc g++ \
  gawk pkg-config wget \
  libacl1-dev libattr1-dev libzstd-dev libssl-dev \
  libxxhash-dev libffi-dev libbz2-dev liblzma-dev zlib1g-dev uuid-dev

RX_ROOT="$(pwd)"
RX_OUT="${RX_ROOT}/rx-out"
SCRATCH="${TMPDIR}"

# Working dir.
cd "${SCRATCH}"

# Install Python.
wget https://www.python.org/ftp/python/3.11.2/Python-3.11.2.tgz
tar zxf Python-3.11.2.tgz
cd Python-3.11.2
./configure --enable-optimizations --enable-shared \
  LDFLAGS="-Wl,-rpath /usr/local/lib"
make
make install
cd "${SCRATCH}"

git clone https://github.com/WayneD/rsync.git
cd rsync
# Ridiculously, this rsync requires commonmark to installed for documentation.
python3 -m pip install commonmark
# If configure sets the size of int32, uint32, etc to all 0, you may need to
# prefix configure with LD_LIBRARY_PATH=/usr/local/lib.
# ./configure LDFLAGS="/usr/local/lib/libxxhash.a"
./configure
make

# Back to rxroot.
cd "${RX_ROOT}"

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pyinstaller rx/client/commands/exec.py \
  --add-binary ${SCRATCH}/rsync/rsync:bin \
  --add-data install:install \
  --paths=. \
  --name rx \
  --onefile

VERSION="0.0.1"
PLATFORM="nix"
TARGET_DIR="rx-${VERSION}"
mkdir -p "${RX_OUT}/${TARGET_DIR}"
cp README.md LICENSE.txt dist/rx "${RX_OUT}/${TARGET_DIR}"
tar --create --directory="${RX_OUT}" --gzip \
  --file=rx-${VERSION}-${PLATFORM}.tar.gz "${TARGET_DIR}"
