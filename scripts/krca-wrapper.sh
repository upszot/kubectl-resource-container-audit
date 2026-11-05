#!/usr/bin/env bash
# Wrapper para KRCA - resuelve la ruta aunque se invoque mediante un symlink.

set -euo pipefail

SOURCE="${BASH_SOURCE[0]}"

# Resolver symlinks (por ejemplo /usr/local/bin/kubectl-krca -> .../scripts/krca-wrapper.sh)
while [ -L "$SOURCE" ]; do
    TARGET="$(readlink "$SOURCE")"
    case "$TARGET" in
        /*) SOURCE="$TARGET" ;;
        *)  SOURCE="$(dirname "$SOURCE")/$TARGET" ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"

if [ -x "$INSTALL_DIR/venv/bin/python3" ]; then
    PYTHON="$INSTALL_DIR/venv/bin/python3"
else
    # Modo sin venv (--no-deps) o instalación antigua.
    PYTHON="${KRCA_PYTHON:-python3}"
    export PYTHONPATH="${INSTALL_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
fi

exec "$PYTHON" "$INSTALL_DIR/scripts/krca" "$@"
