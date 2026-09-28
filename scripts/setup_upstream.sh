#!/usr/bin/env bash
# Clone the paper's repository into ./upstream at the exact commit everything here was tested against.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${GG_UPSTREAM:-$HERE/upstream/grounding-gap}"
COMMIT="b2f7805e50593bcd4df8c83b11cc4fcdb7048ffa"   # 14 May 2026, "Update README.md"
if [ ! -d "$DEST/.git" ]; then
  git clone https://github.com/odychlapanis/grounding-gap.git "$DEST"
fi
git -C "$DEST" checkout -q "$COMMIT"
echo "upstream ready at $DEST ($(git -C "$DEST" rev-parse --short HEAD))"
