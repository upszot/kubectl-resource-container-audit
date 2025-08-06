#!/bin/bash
# KRCA Installer v6.0 - Para versión modular

set -e

# Configuración
KRCA_REPO="https://github.com/upszot/kubectl-resource-container-audit.git"
INSTALL_DIR="/opt/kubectl-resource-container-audit"
SYMLINK_DIR="/usr/local/bin"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Obtener usuario real (incluso con sudo)
REAL_USER=$(logname)
USER_HOME=$(eval echo ~$REAL_USER)

# Instalar dependencias Python
install_python_deps() {
    echo -e "${YELLOW}[INFO] Instalando dependencias Python para $REAL_USER...${NC}"
    
    # Archivo requirements.txt local después del clone
    REQUIREMENTS_FILE="$INSTALL_DIR/requirements.txt"
    
    # Instalar como usuario normal
    if sudo -u $REAL_USER pip install --user -r "$REQUIREMENTS_FILE"; then
        echo -e "${GREEN}[SUCCESS] Dependencias instaladas correctamente${NC}"
        
        # Configurar PATH si es necesario
        if ! grep -q ".local/bin" "$USER_HOME/.bashrc"; then
            echo -e "${YELLOW}[INFO] Configurando PATH en ~/.bashrc${NC}"
            echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$USER_HOME/.bashrc"
            export PATH="$PATH:$USER_HOME/.local/bin"
        fi
    else
        echo -e "${RED}[ERROR] Falló la instalación de dependencias${NC}"
        exit 1
    fi
}

# Instalar wkhtmltopdf
install_wkhtmltopdf() {
    if command -v wkhtmltopdf &>/dev/null; then
        echo -e "${GREEN}[INFO] wkhtmltopdf ya está instalado${NC}"
        return
    fi
    
    echo -e "${YELLOW}[INFO] Instalando wkhtmltopdf...${NC}"
    
    if grep -qi 'fedora' /etc/os-release; then
        dnf install -y wkhtmltopdf || yum install -y wkhtmltopdf
    elif grep -qi 'debian' /etc/os-release; then
        apt-get update && apt-get install -y wkhtmltopdf
    else
        echo -e "${YELLOW}[WARN] Instale wkhtmltopdf manualmente para su distribución${NC}"
    fi
}

# Clonar e instalar KRCA
install_krca() {
    echo -e "${YELLOW}[INFO] Instalando KRCA...${NC}"
    
    # Clonar repositorio
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}[INFO] Actualizando instalación existente...${NC}"
        cd "$INSTALL_DIR"
        git pull origin master
    else
        git clone "$KRCA_REPO" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    # Instalar en modo desarrollo
    echo -e "${YELLOW}[INFO] Instalando paquete Python...${NC}"
    pip install -e .
    
    # Crear symlinks
    ln -sf "$INSTALL_DIR/scripts/krca" "$SYMLINK_DIR/krca"
    ln -sf "$INSTALL_DIR/scripts/krca" "$SYMLINK_DIR/kubectl-krca"
    
    echo -e "${GREEN}[SUCCESS] KRCA instalado correctamente${NC}"
}

# Verificaciones
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}[ERROR] Este script debe ejecutarse como root/sudo${NC}"
    exit 1
fi

# Verificar dependencias básicas
if ! command -v git &>/dev/null; then
    echo -e "${YELLOW}[INFO] Instalando git...${NC}"
    if grep -qi 'fedora' /etc/os-release; then
        dnf install -y git || yum install -y git
    elif grep -qi 'debian' /etc/os-release; then
        apt-get update && apt-get install -y git
    else
        echo -e "${RED}[ERROR] git no está instalado y no se pudo instalar automáticamente${NC}"
        exit 1
    fi
fi

# Proceso de instalación
echo -e "${GREEN}=== Instalador KRCA v6.0 (versión modular) ===${NC}"

install_wkhtmltopdf
install_krca
install_python_deps

echo -e "\n${GREEN}[SUCCESS] Instalación completada!${NC}"
echo -e "Usar con: ${YELLOW}kubectl krca --help${NC}"
echo -e "O directamente: ${YELLOW}krca --help${NC}"
echo -e "Nota: Puede necesitar ejecutar 'source ~/.bashrc' o abrir una nueva terminal"
