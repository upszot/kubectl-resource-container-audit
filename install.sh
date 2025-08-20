#!/bin/bash
# KRCA Installer v6.1

set -e

# Configuración
BRANCH="v4.3"
KRCA_REPO="https://raw.githubusercontent.com/upszot/kubectl-resource-container-audit/$BRANCH"
INSTALL_DIR="/usr/local/share/kubectl-resource-container-audit"
SYMLINK_DIR="/usr/local/bin"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Archivos necesarios 
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
    "scripts/krca-wrapper.sh"
)

create_dirs() {
    echo -e "${YELLOW}[INFO] Creando estructura de directorios...${NC}"
    sudo mkdir -p "$INSTALL_DIR"/{krca,scripts}
}

download_files() {
    echo -e "${YELLOW}[INFO] Descargando archivos desde rama $BRANCH...${NC}"
    
    for file in "${FILES[@]}"; do
        dir="$INSTALL_DIR/$(dirname "$file")"
        sudo mkdir -p "$dir"
        echo -n "Descargando ${file}... "
        
        if sudo curl -sSL "$KRCA_REPO/$file" -o "$INSTALL_DIR/$file"; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
            exit 1
        fi
    done
}

make_executable() {
    echo -e "${YELLOW}[INFO] Configurando permisos ejecutables...${NC}"
    sudo chmod +x "$INSTALL_DIR/scripts/krca"
    sudo chmod +x "$INSTALL_DIR/scripts/krca-wrapper.sh"
}

install_deps() {
    echo -e "${YELLOW}[INFO] Instalando dependencias Python...${NC}"
    pip install -r "$INSTALL_DIR/requirements.txt"
}

setup_symlinks() {
    echo -e "${YELLOW}[INFO] Configurando accesos directos...${NC}"
    # Los symlinks apuntan al WRAPPER, no al script Python
    sudo ln -sf "$INSTALL_DIR/scripts/krca-wrapper.sh" "$SYMLINK_DIR/krca"
    sudo ln -sf "$INSTALL_DIR/scripts/krca-wrapper.sh" "$SYMLINK_DIR/kubectl-krca"
}

verify_install() {
    echo -e "${YELLOW}[INFO] Verificando instalación...${NC}"
    
    if command -v kubectl-krca &>/dev/null; then
        echo -e "${GREEN}[✓] Comandos instalados correctamente${NC}"
    else
        echo -e "${RED}[✗] Los comandos no están disponibles${NC}"
    fi
}

# --- Ejecución principal ---
echo -e "${GREEN}=== Instalador KRCA v6.1 ===${NC}"

[ "$(id -u)" -eq 0 ] || {
    echo -e "${RED}[ERROR] Debes ejecutar como root/sudo${NC}"
    exit 1
}

create_dirs
download_files
make_executable
install_deps
setup_symlinks
verify_install

echo -e "\n${GREEN}[✔] Instalación completada!${NC}"
echo -e "Usar con: ${YELLOW}kubectl krca --help${NC}"
echo -e "O: ${YELLOW}krca --help${NC}"

