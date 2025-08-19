#!/bin/bash
# Wrapper para KRCA - Para uso del instalador

INSTALL_DIR="/usr/local/share/kubectl-resource-container-audit"
export PYTHONPATH="${INSTALL_DIR}:${PYTHONPATH}"

exec python3 "${INSTALL_DIR}/scripts/krca" "$@"

