#!/bin/bash
# This creates a .zip file with the client, a README, and the license.

set -eux

VERSION="$1"
PLATFORM="$2"

ZIP_DIR="${TMPDIR}/rx-${VERSION}"
ZIP_FILE="rx-${VERSION}-${PLATFORM}.zip"

mkdir -p "${ZIP_DIR}"
cp package/README.md LICENSE.txt dist/rx "${ZIP_DIR}"
cd "${TMPDIR}"
zip "${ZIP_FILE}" "${ZIP_DIR}"
cd -

echo "Created ${TMPDIR}/${ZIP_FILE}"
