#!/usr/bin/env bash
# KRCA Uninstaller v7.0

set -Eeuo pipefail

INSTALLER_VERSION="7.1"
DEFAULT_INSTALL_DIR="/usr/local/share/kubectl-resource-container-audit"
DEFAULT_BIN_DIR="/usr/local/bin"

INSTALL_DIR="${KRCA_INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
BIN_DIR="${KRCA_BIN_DIR:-$DEFAULT_BIN_DIR}"
ASSUME_YES=0

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

info() { printf "${BLUE}[INFO]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[ OK ]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$*" >&2; }
die()  { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; exit 1; }

usage() {
    cat <<EOF
${BOLD}KRCA Uninstaller v${INSTALLER_VERSION}${NC}

Uso:
  uninstall.sh [opciones]

Opciones:
  --prefix DIR       Directorio de instalación (def. ${DEFAULT_INSTALL_DIR})
  --bin-dir DIR      Directorio de los symlinks (def. ${DEFAULT_BIN_DIR})
  -y, --yes          No pedir confirmación
  -h, --help         Muestra esta ayuda
  --version          Muestra la versión del desinstalador

Variables de entorno:
  KRCA_INSTALL_DIR, KRCA_BIN_DIR
EOF
}

require_value() {
    [ "$#" -ge 2 ] || die "Falta el valor para la opción $1"
}

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --prefix)
                require_value "$@"
                INSTALL_DIR="$2"
                shift 2
                ;;
            --prefix=*)
                INSTALL_DIR="${1#*=}"
                shift
                ;;
            --bin-dir)
                require_value "$@"
                BIN_DIR="$2"
                shift 2
                ;;
            --bin-dir=*)
                BIN_DIR="${1#*=}"
                shift
                ;;
            -y|--yes)
                ASSUME_YES=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --version)
                echo "KRCA Uninstaller v${INSTALLER_VERSION}"
                exit 0
                ;;
            *)
                die "Opción desconocida: $1 (usá --help)"
                ;;
        esac
    done

    [ -n "$INSTALL_DIR" ] || die "El directorio de instalación no puede estar vacío"
    [ -n "$BIN_DIR" ] || die "El directorio de binarios no puede estar vacío"

    case "$INSTALL_DIR" in
        /|.|..) die "Directorio de instalación inválido: $INSTALL_DIR" ;;
    esac
    case "$BIN_DIR" in
        /|.|..) die "Directorio de binarios inválido: $BIN_DIR" ;;
    esac
}

dir_is_writable() {
    local dir="$1"

    while [ ! -e "$dir" ]; do
        local parent
        parent="$(dirname "$dir")"
        [ "$parent" = "$dir" ] && break
        dir="$parent"
    done

    [ -w "$dir" ]
}

require_privileges() {
    if [ "$(id -u)" -eq 0 ]; then
        return 0
    fi

    if ! dir_is_writable "$INSTALL_DIR" || ! dir_is_writable "$BIN_DIR"; then
        die "Se requieren privilegios de root. Ejecutá con sudo."
    fi
}

legacy_home() {
    if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ] \
        && command -v getent >/dev/null 2>&1; then
        local home
        home="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
        [ -n "$home" ] && printf '%s\n' "$home" && return 0
    fi
    printf '%s\n' "$HOME"
}

remove_legacy_env() {
    local profile="/etc/profile.d/krca.sh"

    if [ -f "$profile" ] && [ -w "$profile" ] \
        && grep -q "KRCA environment configuration" "$profile" 2>/dev/null; then
        rm -f "$profile"
        info "Eliminada configuración antigua: $profile"
    fi

    local bashrc
    bashrc="$(legacy_home)/.bashrc"
    [ -f "$bashrc" ] && [ -w "$bashrc" ] || return 0
    grep -Fq "$INSTALL_DIR" "$bashrc" 2>/dev/null || return 0
    grep -Fq "PYTHONPATH" "$bashrc" 2>/dev/null || return 0

    local tmp
    tmp="$(mktemp "${bashrc}.krca.XXXXXX")"
    if awk -v dir="$INSTALL_DIR" \
        '!(index($0, "PYTHONPATH") && index($0, dir))' "$bashrc" > "$tmp"; then
        cat "$tmp" > "$bashrc"
        rm -f "$tmp"
        info "Eliminada línea PYTHONPATH antigua de $bashrc"
    else
        rm -f "$tmp"
        warn "No se pudo limpiar $bashrc; revisalo manualmente"
    fi
}

remove_symlink() {
    local link="$1"
    local expected="$INSTALL_DIR/scripts/krca-wrapper.sh"

    if [ -L "$link" ]; then
        if [ "$(readlink "$link")" = "$expected" ]; then
            rm -f "$link"
            ok "Eliminado $link"
        else
            warn "Se omite $link: apunta a otro destino ($(readlink "$link"))"
        fi
    elif [ -e "$link" ]; then
        warn "Se omite $link: no es un symlink"
    fi
}

main() {
    parse_args "$@"

    printf "${BOLD}=== KRCA Uninstaller v${INSTALLER_VERSION} ===${NC}\n"

    require_privileges

    local installed_version=""
    if [ -f "$INSTALL_DIR/VERSION" ]; then
        installed_version="$(head -n 1 "$INSTALL_DIR/VERSION" | tr -d '[:space:]')"
    fi

    if [ ! -e "$INSTALL_DIR" ] \
        && [ ! -L "$BIN_DIR/krca" ] \
        && [ ! -L "$BIN_DIR/kubectl-krca" ]; then
        info "KRCA no parece estar instalado en $INSTALL_DIR"
        return 0
    fi

    if [ -n "$installed_version" ]; then
        info "KRCA instalado: v${installed_version}"
    fi

    if [ "$ASSUME_YES" -eq 0 ]; then
        if [ ! -t 0 ]; then
            die "Modo no interactivo: usá --yes para confirmar la desinstalación"
        fi
        printf "Se eliminará %s y los comandos %s/{krca,kubectl-krca}.\n" "$INSTALL_DIR" "$BIN_DIR"
        local answer=""
        read -r -p "¿Continuar? [s/N] " answer || answer=""
        case "$answer" in
            s|S|si|SI|sí|SÍ) ;;
            *) info "Desinstalación cancelada"; return 0 ;;
        esac
    fi

    remove_symlink "$BIN_DIR/krca"
    remove_symlink "$BIN_DIR/kubectl-krca"

    if [ -e "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        ok "Eliminado $INSTALL_DIR"
    fi

    remove_legacy_env

    echo
    ok "Desinstalación completada"
}

main "$@"
