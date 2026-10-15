#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
export PHOENIX_STAGE="$ROOT" PHOENIX_SOURCE_STAGE="$ROOT"
: "${MDX_PARSER_MODULES:?Set MDX_PARSER_MODULES to the locked parser node_modules directory}"
export MDX_PARSER_MODULES
node "$HERE/build_compact.cjs"
python3 "$HERE/audit_phoenix.py"
node "$HERE/apply_extents.cjs"
node "$HERE/verify_compact.cjs"
python3 "$HERE/audit_effects.py"
