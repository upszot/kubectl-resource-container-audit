#!/usr/bin/env bash
# KRCA Installer v7.1
#
# Instalación recomendada:
#   curl -fsSL https://raw.githubusercontent.com/upszot/kubectl-resource-container-audit/master/install.sh | sudo bash
#
# Instalación desde un checkout local:
#   sudo ./install.sh --source .

set -Eeuo pipefail

INSTALLER_VERSION="7.1"
KRCA_REPO="${KRCA_REPO:-upszot/kubectl-resource-container-audit}"
DEFAULT_INSTALL_DIR="/usr/local/share/kubectl-resource-container-audit"
DEFAULT_BIN_DIR="/usr/local/bin"

INSTALL_DIR="${KRCA_INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
BIN_DIR="${KRCA_BIN_DIR:-$DEFAULT_BIN_DIR}"
BRANCH="${KRCA_BRANCH:-master}"
SOURCE_DIR="${KRCA_SOURCE_DIR:-}"
PYTHON_BIN="${KRCA_PYTHON:-python3}"
INSTALL_DEPS=1
ACTION="install"
ASSUME_YES=0

# Colores (sólo si la salida es una terminal)
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

WORK_DIR=""
STAGE_DIR=""
VENV_DIR=""
APP_VERSION=""

info()  { printf "${BLUE}[INFO]${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}[ OK ]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC} %s\n" "$*" >&2; }
die()   { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; exit 1; }

usage() {
    cat <<EOF
${BOLD}KRCA Installer v${INSTALLER_VERSION}${NC}

Uso:
  install.sh [opciones]

Opciones:
  --prefix DIR       Directorio de instalación (def. ${DEFAULT_INSTALL_DIR})
  --bin-dir DIR      Directorio de los symlinks (def. ${DEFAULT_BIN_DIR})
  --branch REF       Rama, tag o commit a instalar (def. master)
  --source DIR       Instala desde un directorio local, sin descargar
  --no-deps          No crea el venv ni instala dependencias Python
  --uninstall        Desinstala KRCA
  -y, --yes          No pedir confirmación al desinstalar
  -h, --help         Muestra esta ayuda
  --version          Muestra la versión del instalador

Variables de entorno:
  KRCA_INSTALL_DIR, KRCA_BIN_DIR, KRCA_BRANCH, KRCA_SOURCE_DIR, KRCA_PYTHON

Ejemplos:
  sudo ./install.sh
  sudo ./install.sh --branch v5.1
  sudo ./install.sh --source .
  sudo ./install.sh --prefix /opt/krca --bin-dir /usr/local/bin
  sudo ./install.sh --uninstall --yes

Notas:
  - Las dependencias se instalan en un venv dentro del directorio de
    instalación, por lo que no se modifican los paquetes del sistema.
  - Para exportar a PDF se requiere wkhtmltopdf (opcional).
EOF
}

# --- Parseo de argumentos ---------------------------------------------------

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
            --branch)
                require_value "$@"
                BRANCH="$2"
                shift 2
                ;;
            --branch=*)
                BRANCH="${1#*=}"
                shift
                ;;
            --source)
                require_value "$@"
                SOURCE_DIR="$2"
                shift 2
                ;;
            --source=*)
                SOURCE_DIR="${1#*=}"
                shift
                ;;
            --no-deps)
                INSTALL_DEPS=0
                shift
                ;;
            --uninstall)
                ACTION="uninstall"
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
                echo "KRCA Installer v${INSTALLER_VERSION}"
                exit 0
                ;;
            *)
                die "Opción desconocida: $1 (usá --help)"
                ;;
        esac
    done

    validate_paths
}

validate_paths() {
    [ -n "$INSTALL_DIR" ] || die "El directorio de instalación no puede estar vacío"
    [ -n "$BIN_DIR" ] || die "El directorio de binarios no puede estar vacío"

    case "$INSTALL_DIR" in
        /|.|..) die "Directorio de instalación inválido: $INSTALL_DIR" ;;
    esac
    case "$BIN_DIR" in
        /|.|..) die "Directorio de binarios inválido: $BIN_DIR" ;;
    esac
}

# --- Utilidades -------------------------------------------------------------

cleanup() {
    [ -z "${WORK_DIR:-}" ] || rm -rf "$WORK_DIR"
    [ -z "${STAGE_DIR:-}" ] || rm -rf "$STAGE_DIR"
    return 0
}
trap cleanup EXIT

# Devuelve 0 si el directorio es escribible o puede crearse.
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
        die "Se requieren privilegios de root. Ejecutá con sudo o elegí directorios escribibles con --prefix/--bin-dir."
    fi
}

check_tools() {
    command -v "$PYTHON_BIN" >/dev/null 2>&1 \
        || die "No se encontró Python ('$PYTHON_BIN'). Instalá python3 o usá KRCA_PYTHON."

    if [ "$INSTALL_DEPS" -eq 1 ]; then
        "$PYTHON_BIN" -m venv --help >/dev/null 2>&1 \
            || die "Python no tiene el módulo venv. En Debian/Ubuntu instalá: sudo apt install python3-venv"
    fi

    if [ -z "$SOURCE_DIR" ]; then
        command -v curl >/dev/null 2>&1 || die "No se encontró curl (necesario para descargar KRCA)"
        command -v tar >/dev/null 2>&1 || die "No se encontró tar (necesario para extraer KRCA)"
    fi

    command -v kubectl >/dev/null 2>&1 \
        || warn "kubectl no está en el PATH. KRCA se instala igual, pero lo necesitás para usarlo."
    command -v wkhtmltopdf >/dev/null 2>&1 \
        || warn "wkhtmltopdf no está instalado. La exportación a PDF no estará disponible."
}

check_python_version() {
    local version
    version="$("$PYTHON_BIN" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"

    if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 8) else 1)'; then
        die "Se requiere Python 3.8 o superior (encontrado: $version)"
    fi

    if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
        warn "KRCA recomienda Python 3.12+. Se continuará con Python $version."
    fi

    info "Python detectado: $version ($PYTHON_BIN)"
}

# --- Obtención del código fuente -------------------------------------------

# La versión de KRCA vive en el archivo VERSION de la raíz del proyecto.
# Para ramas antiguas que no lo tengan, se usa como fallback el valor literal
# que tuvieran en krca/__init__.py.
read_app_version() {
    local src="$1"
    local version=""

    if [ -f "$src/VERSION" ]; then
        version="$(head -n 1 "$src/VERSION" | tr -d '[:space:]')"
    fi

    if [ -z "$version" ] && [ -f "$src/krca/__init__.py" ]; then
        version="$(sed -n 's/^__version__[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$src/krca/__init__.py" | head -n 1)"
    fi

    printf '%s\n' "$version"
}

prepare_source() {
    if [ -n "$SOURCE_DIR" ]; then
        [ -d "$SOURCE_DIR" ] || die "El directorio indicado en --source no existe: $SOURCE_DIR"
        SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
        [ -f "$SOURCE_DIR/krca/__init__.py" ] \
            || die "El directorio --source no parece ser KRCA (falta krca/__init__.py): $SOURCE_DIR"
        APP_VERSION="$(read_app_version "$SOURCE_DIR")"
        [ -n "$APP_VERSION" ] || warn "No se pudo determinar la versión desde VERSION"
        info "Usando código local: $SOURCE_DIR (v${APP_VERSION:-?})"
        return 0
    fi

    WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/krca-install.XXXXXX")"
    local archive="$WORK_DIR/krca.tar.gz"
    local url
    local downloaded=0

    info "Descargando ${KRCA_REPO} (${BRANCH})..."
    for url in \
        "https://github.com/${KRCA_REPO}/archive/refs/heads/${BRANCH}.tar.gz" \
        "https://github.com/${KRCA_REPO}/archive/refs/tags/${BRANCH}.tar.gz" \
        "https://github.com/${KRCA_REPO}/archive/${BRANCH}.tar.gz"
    do
        if curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 15 "$url" -o "$archive" 2>/dev/null; then
            downloaded=1
            break
        fi
    done

    [ "$downloaded" -eq 1 ] \
        || die "No se pudo descargar la rama/tag '$BRANCH'. Verificá el nombre con --branch o usá --source DIR."

    mkdir -p "$WORK_DIR/src"
    tar -xzf "$archive" -C "$WORK_DIR/src" --no-same-owner

    SOURCE_DIR="$(find "$WORK_DIR/src" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    [ -n "$SOURCE_DIR" ] || die "El archivo descargado no tiene el formato esperado"
    [ -f "$SOURCE_DIR/krca/__init__.py" ] || die "El código descargado no contiene el paquete krca"

    APP_VERSION="$(read_app_version "$SOURCE_DIR")"
    [ -n "$APP_VERSION" ] || warn "No se pudo determinar la versión desde VERSION"
    ok "Código descargado correctamente (v${APP_VERSION:-?})"
}

# --- Instalación ------------------------------------------------------------

prepare_venv() {
    if [ "$INSTALL_DEPS" -eq 0 ]; then
        info "Omitiendo la creación del venv (--no-deps)"
        return 0
    fi

    VENV_DIR="$INSTALL_DIR/venv"

    if [ ! -x "$VENV_DIR/bin/python3" ]; then
        info "Creando entorno virtual en $VENV_DIR..."
        mkdir -p "$INSTALL_DIR"
        "$PYTHON_BIN" -m venv "$VENV_DIR" \
            || die "No se pudo crear el entorno virtual. Instalá python3-venv o usá --no-deps."
    fi

    "$VENV_DIR/bin/python3" -m pip --version >/dev/null 2>&1 \
        || die "El entorno virtual no tiene pip. Revisá la instalación de Python/venv."
}

install_dependencies() {
    if [ "$INSTALL_DEPS" -eq 0 ]; then
        warn "Dependencias Python no instaladas. Asegurate de tener tabulate y kubernetes disponibles."
        return 0
    fi

    info "Instalando dependencias Python..."
    "$VENV_DIR/bin/python3" -m pip install \
        --disable-pip-version-check \
        --no-input \
        --upgrade \
        -r "$SOURCE_DIR/requirements.txt" \
        || die "Falló la instalación de dependencias Python"

    ok "Dependencias instaladas en el venv"
}

install_files() {
    info "Instalando archivos en $INSTALL_DIR..."

    mkdir -p "$INSTALL_DIR"

    # Se prepara todo en un directorio temporal dentro del destino para que un
    # fallo no deje la instalación anterior a medio reemplazar.
    STAGE_DIR="$INSTALL_DIR/.stage.$$"
    rm -rf "$STAGE_DIR"
    mkdir -p "$STAGE_DIR"

    cp -R "$SOURCE_DIR/krca" "$STAGE_DIR/krca"
    cp -R "$SOURCE_DIR/scripts" "$STAGE_DIR/scripts"

    local file
    for file in VERSION requirements.txt LICENSE README.md Changelog.md; do
        [ -f "$SOURCE_DIR/$file" ] && cp "$SOURCE_DIR/$file" "$STAGE_DIR/$file"
    done

    # Limpiar cachés de Python que puedan venir del checkout local.
    find "$STAGE_DIR" -type d -name __pycache__ -prune -exec rm -rf {} +
    find "$STAGE_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

    # Verificar archivos que el instalador anterior no descargaba.
    local asset
    for asset in styles.css resize.css resize.js; do
        [ -f "$STAGE_DIR/krca/$asset" ] \
            || die "Falta el archivo requerido krca/$asset en el código fuente"
    done

    # Reemplazar sólo el código; el venv se conserva entre actualizaciones.
    rm -rf "$INSTALL_DIR/krca" "$INSTALL_DIR/scripts"
    mv "$STAGE_DIR/krca" "$INSTALL_DIR/krca"
    mv "$STAGE_DIR/scripts" "$INSTALL_DIR/scripts"

    for file in "$STAGE_DIR"/*; do
        [ -f "$file" ] && mv "$file" "$INSTALL_DIR/"
    done
    rmdir "$STAGE_DIR" 2>/dev/null || true
    STAGE_DIR=""

    # Permisos consistentes. El código queda propiedad de root cuando se
    # instala con sudo (cp -R no preserva el owner del checkout).
    find "$INSTALL_DIR/krca" "$INSTALL_DIR/scripts" -type d -exec chmod 755 {} +
    find "$INSTALL_DIR/krca" "$INSTALL_DIR/scripts" -type f -exec chmod 644 {} +
    chmod 755 "$INSTALL_DIR/scripts/krca" "$INSTALL_DIR/scripts/krca-wrapper.sh"

    ok "Archivos instalados"
}

setup_symlinks() {
    info "Configurando comandos en $BIN_DIR..."

    mkdir -p "$BIN_DIR"
    ln -sfn "$INSTALL_DIR/scripts/krca-wrapper.sh" "$BIN_DIR/krca"
    ln -sfn "$INSTALL_DIR/scripts/krca-wrapper.sh" "$BIN_DIR/kubectl-krca"

    ok "Symlinks creados: krca, kubectl-krca"
}

# Elimina restos del instalador antiguo (PYTHONPATH global). El wrapper nuevo
# resuelve las rutas por sí mismo, así que ya no es necesario.
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

verify_install() {
    info "Verificando instalación..."

    local python="$PYTHON_BIN"
    if [ -n "$VENV_DIR" ] && [ -x "$VENV_DIR/bin/python3" ]; then
        python="$VENV_DIR/bin/python3"
    fi

    if (cd / && PYTHONPATH="$INSTALL_DIR" "$python" -c "import krca") >/dev/null 2>&1; then
        local version
        version="$(cd / && PYTHONPATH="$INSTALL_DIR" "$python" -c "import krca; print(krca.__version__)" 2>/dev/null || echo "?")"
        if [ -n "$APP_VERSION" ] && [ "$version" != "$APP_VERSION" ]; then
            if [ "$INSTALL_DEPS" -eq 1 ]; then
                die "Versión inconsistente: se esperaba v${APP_VERSION} pero el paquete reporta v${version}"
            else
                warn "Versión inconsistente: se esperaba v${APP_VERSION} pero el paquete reporta v${version}"
            fi
        else
            ok "Paquete Python importable (v${version})"
        fi
    elif [ "$INSTALL_DEPS" -eq 1 ]; then
        die "No se pudo importar el paquete krca. Revisá la instalación de dependencias."
    else
        warn "No se pudo importar el paquete krca. Revisá las dependencias (probá sin --no-deps)."
    fi

    if [ -x "$BIN_DIR/kubectl-krca" ]; then
        local output
        if output="$("$BIN_DIR/kubectl-krca" --version 2>&1)"; then
            if [ -n "$APP_VERSION" ]; then
                case "$output" in
                    *"v${APP_VERSION}"*) ok "$output" ;;
                    *)
                        if [ "$INSTALL_DEPS" -eq 1 ]; then
                            die "El comando reporta una versión distinta a v${APP_VERSION}: $output"
                        else
                            warn "El comando reporta una versión distinta a v${APP_VERSION}: $output"
                        fi
                        ;;
                esac
            else
                ok "$output"
            fi
        elif [ "$INSTALL_DEPS" -eq 1 ]; then
            die "El comando kubectl-krca no respondió correctamente: $output"
        else
            warn "El comando kubectl-krca no respondió correctamente: $output"
        fi
    else
        die "No se encontró el ejecutable $BIN_DIR/kubectl-krca"
    fi
}

print_summary() {
    echo
    printf "${GREEN}${BOLD}[✔] Instalación completada${NC}\n\n"
    if [ -n "$APP_VERSION" ]; then
        printf "  Versión KRCA:      v%s\n" "$APP_VERSION"
    fi
    printf "  Comando principal: ${YELLOW}kubectl krca --help${NC}\n"
    printf "  Alias directo:     ${YELLOW}krca --help${NC}\n"
    printf "  Instalado en:      %s\n" "$INSTALL_DIR"

    case ":$PATH:" in
        *":$BIN_DIR:"*) ;;
        *) warn "Agregá $BIN_DIR al PATH para usar los comandos directamente." ;;
    esac
}

# --- Desinstalación ---------------------------------------------------------

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

uninstall() {
    require_privileges

    if [ ! -e "$INSTALL_DIR" ] \
        && [ ! -L "$BIN_DIR/krca" ] \
        && [ ! -L "$BIN_DIR/kubectl-krca" ]; then
        info "KRCA no parece estar instalado en $INSTALL_DIR"
        return 0
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

    rm -rf "$INSTALL_DIR"
    ok "Eliminado $INSTALL_DIR"

    remove_legacy_env

    echo
    ok "Desinstalación completada"
}

# --- Main -------------------------------------------------------------------

main() {
    parse_args "$@"

    printf "${BOLD}=== KRCA Installer v${INSTALLER_VERSION} ===${NC}\n"

    if [ "$ACTION" = "uninstall" ]; then
        uninstall
        return 0
    fi

    require_privileges
    check_tools
    check_python_version
    prepare_source
    prepare_venv
    install_dependencies
    install_files
    setup_symlinks
    remove_legacy_env
    verify_install
    print_summary
}

main "$@"
