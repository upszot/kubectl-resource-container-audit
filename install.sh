#!/usr/bin/env bash
# KRCA Installer v7.2
#
# Instalación recomendada:
#   curl -fsSL https://raw.githubusercontent.com/upszot/kubectl-resource-container-audit/master/install.sh | sudo bash
#
# Instalación desde un checkout local:
#   sudo ./install.sh --source .

set -Eeuo pipefail

INSTALLER_VERSION="7.2"
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
PATH_BIN=""
RESOLVED_BIN=""
REPORTED_KUBECTL_VERSION=""

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
  --doctor           Diagnostica una instalación existente (no instala)
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
  sudo ./install.sh --doctor
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
            --doctor)
                ACTION="doctor"
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

# Elimina una distribución 'krca' residual del venv. Si quedó de pruebas
# anteriores (pip install ., wheel local, etc.) puede tapar el código
# instalado y reportar una versión distinta.
purge_venv_krca() {
    local venv_python="$INSTALL_DIR/venv/bin/python3"

    [ -x "$venv_python" ] || return 0
    "$venv_python" -m pip show krca >/dev/null 2>&1 || return 0

    info "Eliminando paquete krca residual del venv..."
    if "$venv_python" -m pip uninstall -y krca >/dev/null 2>&1; then
        ok "Paquete krca residual eliminado"
    else
        warn "No se pudo eliminar el paquete krca residual del venv"
    fi
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

    # El VERSION copiado es la fuente de verdad de la instalación: debe ser
    # exactamente el mismo que se detectó en el código fuente.
    local installed_version=""
    [ -f "$INSTALL_DIR/VERSION" ] \
        && installed_version="$(head -n 1 "$INSTALL_DIR/VERSION" | tr -d '[:space:]')"
    if [ -z "$installed_version" ]; then
        die "No se pudo instalar $INSTALL_DIR/VERSION"
    fi
    if [ -n "$APP_VERSION" ] && [ "$installed_version" != "$APP_VERSION" ]; then
        die "VERSION instalado ($installed_version) distinto al esperado ($APP_VERSION)"
    fi

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

# --- Diagnóstico de versión e instalación ------------------------------------

# Resuelve un symlink de forma portable (sin depender de readlink -f).
resolve_link() {
    local path="$1"
    local target

    while [ -L "$path" ]; do
        target="$(readlink "$path")"
        case "$target" in
            /*) path="$target" ;;
            *) path="$(dirname "$path")/$target" ;;
        esac
    done

    printf '%s\n' "$path"
}

resolve_python() {
    if [ -x "$INSTALL_DIR/venv/bin/python3" ]; then
        printf '%s\n' "$INSTALL_DIR/venv/bin/python3"
    else
        printf '%s\n' "$PYTHON_BIN"
    fi
}

installed_version_file() {
    [ -f "$INSTALL_DIR/VERSION" ] || return 0
    head -n 1 "$INSTALL_DIR/VERSION" | tr -d '[:space:]'
}

# Imprime un atributo del paquete instalado (__version__, __file__).
python_krca_field() {
    local field="$1"
    local python
    python="$(resolve_python)"

    (cd / && PYTHONPATH="$INSTALL_DIR" "$python" \
        -c "import krca; print(krca.${field})" 2>/dev/null) || true
}

bin_command_version() {
    [ -x "$BIN_DIR/kubectl-krca" ] || return 0
    "$BIN_DIR/kubectl-krca" --version 2>/dev/null || true
}

path_binary() {
    command -v kubectl-krca 2>/dev/null || true
}

check_path_resolution() {
    PATH_BIN="$(path_binary)"

    if [ -z "$PATH_BIN" ]; then
        warn "$BIN_DIR no está en PATH; 'kubectl krca' no encontrará el plugin."
        return 0
    fi

    RESOLVED_BIN="$(resolve_link "$PATH_BIN")"
    local expected_bin
    expected_bin="$(resolve_link "$BIN_DIR/kubectl-krca")"

    if [ "$RESOLVED_BIN" != "$expected_bin" ]; then
        warn "Hay otro 'kubectl-krca' con prioridad en PATH:"
        warn "  en uso:    $PATH_BIN -> $RESOLVED_BIN"
        warn "  instalado: $expected_bin"
        warn "Por eso 'kubectl krca' puede mostrar una versión distinta."
        warn "Revisá con: type -a kubectl-krca  (y luego: sudo ./install.sh --doctor)"
    else
        ok "kubectl-krca resuelve a la instalación ($PATH_BIN)"
    fi
}

verify_install() {
    info "Verificando instalación..."

    local expected="${APP_VERSION:-}"
    local file_version python_version python_file command_version
    file_version="$(installed_version_file)"
    python_version="$(python_krca_field __version__)"
    python_file="$(python_krca_field __file__)"
    command_version="$(bin_command_version)"

    [ -n "$expected" ] || expected="$file_version"

    if [ -z "$file_version" ]; then
        die "No se encontró $INSTALL_DIR/VERSION"
    fi
    if [ -n "$expected" ] && [ "$file_version" != "$expected" ]; then
        die "VERSION instalado (v$file_version) distinto al esperado (v$expected)"
    fi
    ok "VERSION instalado: v$file_version"

    if [ -z "$python_version" ]; then
        if [ "$INSTALL_DEPS" -eq 1 ]; then
            die "No se pudo importar krca con $(resolve_python)"
        fi
        warn "No se pudo importar krca; revisá tabulate/kubernetes"
    else
        case "$python_file" in
            "$INSTALL_DIR"/*) ;;
            *) warn "import krca resuelve fuera de la instalación: $python_file" ;;
        esac

        if [ "$python_version" != "$expected" ]; then
            if [ "$INSTALL_DEPS" -eq 1 ]; then
                die "El módulo reporta v$python_version (esperado v$expected) desde $python_file"
            fi
            warn "El módulo reporta v$python_version (esperado v$expected)"
        else
            ok "Paquete Python importable (v$python_version)"
        fi
    fi

    if [ -z "$command_version" ]; then
        if [ "$INSTALL_DEPS" -eq 1 ]; then
            die "No responde $BIN_DIR/kubectl-krca --version"
        fi
        warn "No responde $BIN_DIR/kubectl-krca --version"
    else
        case "$command_version" in
            *"v${expected}"*) ok "$command_version" ;;
            *)
                if [ "$INSTALL_DEPS" -eq 1 ]; then
                    die "El comando reporta '$command_version' (esperado v$expected)"
                fi
                warn "El comando reporta '$command_version' (esperado v$expected)"
                ;;
        esac
    fi

    check_path_resolution

    if command -v kubectl >/dev/null 2>&1; then
        REPORTED_KUBECTL_VERSION="$(kubectl krca --version 2>&1 || true)"
        case "$REPORTED_KUBECTL_VERSION" in
            *"v${expected}"*) ok "kubectl krca: $REPORTED_KUBECTL_VERSION" ;;
            *)
                warn "kubectl krca reporta '$REPORTED_KUBECTL_VERSION' (esperado v$expected)."
                warn "Ejecutá sin sudo para diagnosticar: ./install.sh --doctor"
                ;;
        esac
    fi
}

doctor() {
    if [ ! -d "$INSTALL_DIR" ]; then
        die "No hay una instalación de KRCA en $INSTALL_DIR"
    fi

    printf "${BOLD}=== KRCA Doctor ===${NC}\n"
    printf "  Instalación: %s\n" "$INSTALL_DIR"
    printf "  Binarios:    %s\n" "$BIN_DIR"
    printf "  Python:      %s\n" "$(resolve_python)"

    local problems=0
    local file_version python_version python_file command_version
    file_version="$(installed_version_file)"
    python_version="$(python_krca_field __version__)"
    python_file="$(python_krca_field __file__)"
    command_version="$(bin_command_version)"

    if [ -n "$file_version" ]; then
        ok "VERSION instalado: v$file_version"
    else
        warn "Falta $INSTALL_DIR/VERSION"
        problems=$((problems + 1))
    fi

    if [ -n "$python_version" ]; then
        printf "  krca:        %s\n" "$python_file"
        printf "  __version__: %s\n" "$python_version"

        if [ -n "$file_version" ] && [ "$python_version" != "$file_version" ]; then
            warn "La versión importada no coincide con el VERSION instalado"
            problems=$((problems + 1))
        fi

        case "$python_file" in
            "$INSTALL_DIR"/*) ;;
            *)
                warn "El paquete se importa desde fuera de la instalación"
                problems=$((problems + 1))
                ;;
        esac
    else
        warn "No se pudo importar krca"
        problems=$((problems + 1))
    fi

    if [ -n "$command_version" ]; then
        printf "  kubectl-krca: %s\n" "$command_version"
        if [ -n "$file_version" ]; then
            case "$command_version" in
                *"v${file_version}"*) ;;
                *)
                    warn "El comando no reporta la versión instalada"
                    problems=$((problems + 1))
                    ;;
            esac
        fi
    else
        warn "$BIN_DIR/kubectl-krca no responde"
        problems=$((problems + 1))
    fi

    PATH_BIN="$(path_binary)"
    if [ -z "$PATH_BIN" ]; then
        warn "kubectl-krca no está en PATH"
        problems=$((problems + 1))
    else
        RESOLVED_BIN="$(resolve_link "$PATH_BIN")"
        printf "  PATH:        %s -> %s\n" "$PATH_BIN" "$RESOLVED_BIN"
        if [ "$RESOLVED_BIN" != "$(resolve_link "$BIN_DIR/kubectl-krca")" ]; then
            warn "Otro binario tiene prioridad sobre la instalación"
            problems=$((problems + 1))
        fi
    fi

    if command -v kubectl >/dev/null 2>&1; then
        REPORTED_KUBECTL_VERSION="$(kubectl krca --version 2>&1 || true)"
        printf "  kubectl krca: %s\n" "$REPORTED_KUBECTL_VERSION"
        if [ -n "$file_version" ]; then
            case "$REPORTED_KUBECTL_VERSION" in
                *"v${file_version}"*) ;;
                *)
                    warn "'kubectl krca' no reporta la versión instalada"
                    problems=$((problems + 1))
                    ;;
            esac
        fi
    fi

    if [ -x "$INSTALL_DIR/venv/bin/pip" ] \
        && "$INSTALL_DIR/venv/bin/pip" show krca >/dev/null 2>&1; then
        warn "Hay una distribución 'krca' instalada dentro del venv (puede tapar el código instalado)"
        "$INSTALL_DIR/venv/bin/pip" show krca 2>/dev/null | sed -n 's/^Version: /  Versión en venv: /p'
        problems=$((problems + 1))
    fi

    echo
    if [ "$problems" -eq 0 ]; then
        ok "Instalación consistente (v$file_version)"
        return 0
    fi

    warn "Se encontraron $problems inconsistencia(s)."
    printf "  Para reinstalar limpio: sudo %s --source .\n" "$(basename "$0")"
    return 1
}

print_summary() {
    echo
    printf "${GREEN}${BOLD}[✔] Instalación completada${NC}\n\n"
    if [ -n "$APP_VERSION" ]; then
        printf "  Versión KRCA:      v%s\n" "$APP_VERSION"
    fi
    printf "  Instalado en:      %s\n" "$INSTALL_DIR"
    printf "  Binario:           %s\n" "$BIN_DIR/kubectl-krca"
    if [ -n "${REPORTED_KUBECTL_VERSION:-}" ]; then
        printf "  kubectl krca:      %s\n" "$REPORTED_KUBECTL_VERSION"
    fi
    printf "  Comando principal: ${YELLOW}kubectl krca --help${NC}\n"
    printf "  Alias directo:     ${YELLOW}krca --help${NC}\n"

    if [ -n "${RESOLVED_BIN:-}" ] \
        && [ "$RESOLVED_BIN" != "$(resolve_link "$BIN_DIR/kubectl-krca")" ]; then
        warn "kubectl krca usa $RESOLVED_BIN (no la instalación recién realizada)."
        warn "Desinstalá ese binario o reordená PATH; luego ejecutá: ./install.sh --doctor"
    fi

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

    if [ "$ACTION" = "doctor" ]; then
        printf "${BOLD}=== KRCA Installer v${INSTALLER_VERSION} ===${NC}\n"
        doctor
        return $?
    fi

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
    purge_venv_krca
    install_dependencies
    install_files
    setup_symlinks
    remove_legacy_env
    verify_install
    print_summary
}

main "$@"
