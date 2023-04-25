#!/bin/bash
# This creates a .zip file with the client, a README, and the license.

set -eux

VERSION="$1"
PLATFORM="$2"

ZIP_BASENAME="rx-${VERSION}"
ZIP_DIR="${TMPDIR}/${ZIP_BASENAME}"
ZIP_FILE="rx-${VERSION}-${PLATFORM}.zip"

# Copy files to a working dir.
mkdir -p "${ZIP_DIR}"
cp package/README.md LICENSE.txt rx-out/dist/rx "${ZIP_DIR}"

cd "${TMPDIR}"
# Clean up if there's an old version around.
rm -f "${ZIP_FILE}"
zip -r "${ZIP_FILE}" "rx-${VERSION}"
cd -

cp ${TMPDIR}/${ZIP_FILE} rx-out/
echo "Created rx-out/${ZIP_FILE}"
