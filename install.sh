#!/bin/bash
# KRCA Installer v6.2

set -e

# Configuración
BRANCH="v4.4"
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

set_permissions() {
    echo -e "${YELLOW}[INFO] Configurando permisos...${NC}"
    # Permisos adecuados para directorios y archivos (755 en lugar de 700)
    sudo chmod -R 755 "$INSTALL_DIR"
    sudo chmod +x "$INSTALL_DIR/scripts/krca"
    sudo chmod +x "$INSTALL_DIR/scripts/krca-wrapper.sh"
}

install_deps() {
    echo -e "${YELLOW}[INFO] Instalando dependencias Python...${NC}"
    # Instalar globalmente para todos los usuarios
    pip install -r "$INSTALL_DIR/requirements.txt"
}

setup_symlinks() {
    echo -e "${YELLOW}[INFO] Configurando accesos directos...${NC}"
    # Los symlinks apuntan al WRAPPER, no al script Python
    sudo ln -sf "$INSTALL_DIR/scripts/krca-wrapper.sh" "$SYMLINK_DIR/krca"
    sudo ln -sf "$INSTALL_DIR/scripts/krca-wrapper.sh" "$SYMLINK_DIR/kubectl-krca"
}

setup_environment() {
    echo -e "${YELLOW}[INFO] Configurando variables de entorno...${NC}"
    
    # Configurar PYTHONPATH globalmente para todos los usuarios
    local PYTHONPATH_CONFIG="/etc/profile.d/krca.sh"
    
    sudo bash -c "cat > $PYTHONPATH_CONFIG" << EOF
# KRCA environment configuration
export PYTHONPATH="\$PYTHONPATH:$INSTALL_DIR"
EOF
    
    sudo chmod 644 "$PYTHONPATH_CONFIG"
    
    # También agregar al usuario actual si existe .bashrc
    if [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "PYTHONPATH.*$INSTALL_DIR" "$HOME/.bashrc"; then
            echo "export PYTHONPATH=\"\$PYTHONPATH:$INSTALL_DIR\"" >> "$HOME/.bashrc"
        fi
    fi
    
    # Aplicar cambios al shell actual
    export PYTHONPATH="$PYTHONPATH:$INSTALL_DIR"
}

verify_install() {
    echo -e "${YELLOW}[INFO] Verificando instalación...${NC}"
    
    # Forzar actualización del cache de comandos
    hash -r
    
    if command -v kubectl-krca &>/dev/null && command -v krca &>/dev/null; then
        echo -e "${GREEN}[✓] Comandos instalados correctamente${NC}"
        
        # Verificar que Python puede importar los módulos
        if python3 -c "import krca; print('KRCA module loaded successfully')" 2>/dev/null; then
            echo -e "${GREEN}[✓] Módulos Python accesibles${NC}"
        else
            echo -e "${YELLOW}[!] PYTHONPATH puede requerir reinicio de sesión${NC}"
        fi
    else
        echo -e "${YELLOW}[!] Los comandos pueden requerir reinicio de sesión${NC}"
        echo -e "${YELLOW}[!] O ejecuta: source /etc/profile.d/krca.sh${NC}"
    fi
}

cleanup_old_install() {
    echo -e "${YELLOW}[INFO] Limpiando instalaciones anteriores...${NC}"
    # Remover symlinks viejos
    sudo rm -f "$SYMLINK_DIR/krca" "$SYMLINK_DIR/kubectl-krca"
    # Remover configuraciones viejas de entorno
    sudo rm -f /etc/profile.d/krca.sh
}

# --- Ejecución principal ---
echo -e "${GREEN}=== Instalador KRCA v6.2 ===${NC}"

[ "$(id -u)" -eq 0 ] || {
    echo -e "${RED}[ERROR] Debes ejecutar como root/sudo${NC}"
    exit 1
}

cleanup_old_install
create_dirs
download_files
set_permissions
install_deps
setup_symlinks
setup_environment
verify_install

echo -e "\n${GREEN}[✔] Instalación completada!${NC}"
echo -e "Usar con: ${YELLOW}kubectl krca --help${NC}"
echo -e "O: ${YELLOW}krca --help${NC}"
echo -e "${YELLOW}Nota: Puede necesitar reiniciar la sesión o ejecutar:${NC}"
echo -e "${YELLOW}source /etc/profile.d/krca.sh${NC}"
