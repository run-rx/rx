#!/bin/bash
# This creates a .tar.gz file with the client, a README, and the license.

set -eux

VERSION="$1"
PLATFORM="osx"

ZIP_BASENAME="rx-${VERSION}"
ZIP_DIR="${TMPDIR}/${ZIP_BASENAME}"
ZIP_FILE="rx-${VERSION}-${PLATFORM}.tar.gz"

# Copy files to a working dir.
mkdir -p "${ZIP_DIR}"
cp package/README.md LICENSE.txt dist/rx "${ZIP_DIR}"

# Clean up if there's an old version around.
rm -f "${ZIP_FILE}"
tar --create --directory="${TMPDIR}" --gzip --uid=0 --gid=0 \
  --file "${ZIP_FILE}" "rx-${VERSION}"

echo "Created ${ZIP_FILE}"
