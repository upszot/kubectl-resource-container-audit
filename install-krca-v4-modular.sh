#!/bin/bash
# KRCA Installer v5.8 - Versión corregida

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
)

# Obtener usuario real
REAL_USER=$(logname)
USER_HOME=$(eval echo ~$REAL_USER)

create_dirs() {
    echo -e "${YELLOW}[INFO] Creando estructura de directorios...${NC}"
    sudo mkdir -p "$INSTALL_DIR"/{krca,scripts}
    sudo chown -R $REAL_USER:$REAL_USER "$INSTALL_DIR"
}

download_files() {
    echo -e "${YELLOW}[INFO] Descargando archivos desde rama $BRANCH...${NC}"
    
    for file in "${FILES[@]}"; do
        dir="$INSTALL_DIR/$(dirname "$file")"
        mkdir -p "$dir"
        echo -n "Descargando ${file}... "
        
        if sudo -u $REAL_USER curl -sSL "$KRCA_REPO/$file" -o "$INSTALL_DIR/$file"; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
            exit 1
        fi
    done
}

patch_files() {
    echo -e "${YELLOW}[INFO] Aplicando parches de compatibilidad...${NC}"
    
    # 1. Parche para core.py
    sudo -u $REAL_USER sed -i \
        $'s/^from \\.utils import calculate_percentage_diff$/try:\\\n    from .utils import calculate_percentage_diff\\\nexcept ImportError:\\\n    from .utils import KRCAUtils\\\n    calculate_percentage_diff = KRCAUtils.calculate_percentage_diff\\\n/' \
        "$INSTALL_DIR/krca/core.py"
    
    # 2. Permisos para el script
    sudo -u $REAL_USER chmod +x "$INSTALL_DIR/scripts/krca"
}

install_deps() {
    echo -e "${YELLOW}[INFO] Instalando dependencias Python...${NC}"
    
    # Instalar como usuario normal
    if sudo -u $REAL_USER pip install --user -r "$INSTALL_DIR/requirements.txt"; then
        echo -e "${GREEN}[✓] Dependencias instaladas${NC}"
        
        # Configurar PATH si es necesario
        if ! grep -q ".local/bin" "$USER_HOME/.bashrc"; then
            echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$USER_HOME/.bashrc"
            export PATH="$PATH:$USER_HOME/.local/bin"
        fi
    else
        echo -e "${RED}[✗] Falló la instalación de dependencias${NC}"
        exit 1
    fi
}

setup_symlinks() {
    echo -e "${YELLOW}[INFO] Configurando accesos directos...${NC}"
    sudo ln -sf "$INSTALL_DIR/scripts/krca" "$SYMLINK_DIR/krca"
    sudo ln -sf "$INSTALL_DIR/scripts/krca" "$SYMLINK_DIR/kubectl-krca"
}

verify_install() {
    echo -e "${YELLOW}[INFO] Verificando instalación...${NC}"
    
    # Verificar como usuario normal
    if sudo -u $REAL_USER bash -c 'command -v kubectl-krca &>/dev/null'; then
        echo -e "${GREEN}[✓] Comandos instalados correctamente${NC}"
    else
        echo -e "${RED}[✗] Los comandos no están disponibles${NC}"
        echo -e "${YELLOW}Ejecuta: source ~/.bashrc o abre una nueva terminal${NC}"
    fi
}

# --- Ejecución principal ---
echo -e "${GREEN}=== Instalador KRCA v5.8 (rama $BRANCH) ===${NC}"

[ "$(id -u)" -eq 0 ] || {
    echo -e "${RED}[ERROR] Debes ejecutar como root/sudo${NC}"
    exit 1
}

create_dirs
download_files
patch_files
install_deps
setup_symlinks
verify_install

echo -e "\n${GREEN}[✔] Instalación completada!${NC}"
echo -e "Usar con: ${YELLOW}kubectl krca --help${NC}"
echo -e "O: ${YELLOW}krca --help${NC}"
echo -e "\nSi los comandos no funcionan inmediatamente:"
echo -e "1. Ejecuta: ${YELLOW}source ~/.bashrc${NC}"
echo -e "2. O abre una nueva terminal"
