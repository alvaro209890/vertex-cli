#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_FILE="$ROOT_DIR/patches/vertex-cli-disable-anthropic-login.patch"

cd "$ROOT_DIR"

if git apply --check "$PATCH_FILE" >/dev/null 2>&1; then
  git apply "$PATCH_FILE"
  echo "Applied Vertex CLI patches."
  exit 0
fi

if git apply --reverse --check "$PATCH_FILE" >/dev/null 2>&1; then
  echo "Vertex CLI patches are already applied."
  exit 0
fi

echo "Could not apply Vertex CLI patches." >&2
echo "The vendored CLI bundle likely changed; refresh the patch against vendor/vertex-cli/dist/cli.mjs." >&2
exit 1
