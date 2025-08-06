#!/bin/bash
# KRCA Installer v5.7 - Versión definitiva para estructura modular

set -e

# Configuración
BRANCH="v4.0"
KRCA_REPO="https://raw.githubusercontent.com/upszot/kubectl-resource-container-audit/$BRANCH"
INSTALL_DIR="/usr/local/share/kubectl-resource-container-audit"
SYMLINK_DIR="/usr/local/bin"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Archivos necesarios (en orden de dependencia)
FILES=(
    "requirements.txt"
    "krca/__init__.py"
    "krca/utils.py"
    "krca/models.py"
    "krca/kubectl.py"
    "krca/colorizer.py"
    "krca/exporter.py"
    "krca/cli.py"
    "krca/core.py"
    "scripts/krca"
)

# --- Funciones mejoradas ---

create_dirs() {
    echo -e "${YELLOW}[INFO] Creando estructura de directorios...${NC}"
    sudo mkdir -p "$INSTALL_DIR"/{krca,scripts}
    sudo chown -R $(id -un):$(id -gn) "$INSTALL_DIR"
}

download_files() {
    echo -e "${YELLOW}[INFO] Descargando archivos desde rama $BRANCH...${NC}"
    
    for file in "${FILES[@]}"; do
        local dir="$INSTALL_DIR/$(dirname "$file")"
        mkdir -p "$dir"
        echo -n "Descargando ${file}... "
        
        if curl -sSL "$KRCA_REPO/$file" -o "$INSTALL_DIR/$file"; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
            echo -e "${RED}[ERROR] Falló al descargar $file${NC}"
            exit 1
        fi
    done
}

patch_files() {
    echo -e "${YELLOW}[INFO] Aplicando parches de compatibilidad...${NC}"
    
    # 1. Asegurar que core.py use la importación compatible
    sed -i $'s/^from \\.utils import calculate_percentage_diff$/try:\\\n    from .utils import calculate_percentage_diff\\\nexcept ImportError:\\\n    from .utils import KRCAUtils\\\n    calculate_percentage_diff = KRCAUtils.calculate_percentage_diff\\\n/' "$INSTALL_DIR/krca/core.py"
    
    # 2. Asegurar que el script principal tenga permisos
    chmod +x "$INSTALL_DIR/scripts/krca"
}

install_deps() {
    echo -e "${YELLOW}[INFO] Instalando dependencias Python...${NC}"
    local user_home=$(eval echo ~$(id -un))
    
    if ! pip install --user -r "$INSTALL_DIR/requirements.txt"; then
        echo -e "${RED}[ERROR] Falló la instalación de dependencias${NC}"
        echo -e "${YELLOW}Intente manualmente con: pip install -r $INSTALL_DIR/requirements.txt${NC}"
        exit 1
    fi
    
    # Agregar PATH si no existe
    if ! grep -q ".local/bin" "$user_home/.bashrc"; then
        echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$user_home/.bashrc"
        export PATH="$PATH:$user_home/.local/bin"
    fi
}

setup_symlinks() {
    echo -e "${YELLOW}[INFO] Configurando accesos directos...${NC}"
    sudo ln -sf "$INSTALL_DIR/scripts/krca" "$SYMLINK_DIR/krca"
    sudo ln -sf "$INSTALL_DIR/scripts/krca" "$SYMLINK_DIR/kubectl-krca"
}

verify_install() {
    echo -e "${YELLOW}[INFO] Verificando instalación...${NC}"
    if ! command -v kubectl-krca &>/dev/null; then
        echo -e "${RED}[ERROR] No se pudo encontrar el comando instalado${NC}"
        exit 1
    fi
    
    if ! kubectl-krca --version &>/dev/null; then
        echo -e "${RED}[ERROR] La instalación no funciona correctamente${NC}"
        exit 1
    fi
}

# --- Ejecución principal ---

echo -e "${GREEN}=== Instalador KRCA v5.7 (rama $BRANCH) ===${NC}"

# Requiere root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}[ERROR] Debes ejecutar este script como root/sudo${NC}"
    exit 1
fi

# Flujo de instalación
create_dirs
download_files
patch_files
install_deps
setup_symlinks
verify_install

# Mensaje final
echo -e "\n${GREEN}[✔] Instalación completada con éxito${NC}"
echo -e "Comandos disponibles:"
echo -e "  ${YELLOW}krca --help${NC}"
echo -e "  ${YELLOW}kubectl krca --help${NC}"
echo -e "\nNota: Si los comandos no funcionan inmediatamente, ejecuta:"
echo -e "      ${YELLOW}source ~/.bashrc${NC} o abre una nueva terminal"
