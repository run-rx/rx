#!/bin/bash
# This creates a .zip file with the client, a README, and the license.

set -eux

VERSION="$1"

pyinstaller --onefile rx.spec

ZIP_DIR="${TMPDIR}/rx"
mkdir -p "${ZIP_DIR}"
cp package/README.md LICENSE.txt dist/rx/rx "${ZIP_DIR}"
cd "${TMPDIR}"
zip "rx-${VERSION}.zip" rx
cd -

echo "Created ${TMPDIR}/rx-${VERSION}.zip"
