#!/bin/bash
# KRCA Installer v5.1 - Solución definitiva

set -e

# Configuración
KRCA_REPO="https://raw.githubusercontent.com/upszot/kubectl-resource-container-audit/master"
REQUIREMENTS_URL="$KRCA_REPO/requirements.txt"
SCRIPT_URL="$KRCA_REPO/kubectl-resource-container-audit.py"

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
    
    # Crear archivo temporal en el home del usuario
    TEMP_FILE="$USER_HOME/krca_requirements.txt"
    sudo -u $REAL_USER curl -sSL $REQUIREMENTS_URL -o "$TEMP_FILE"
    
    # Instalar como usuario normal
    if sudo -u $REAL_USER pip install --user -r "$TEMP_FILE"; then
        echo -e "${GREEN}[SUCCESS] Dependencias instaladas correctamente${NC}"
        
        # Configurar PATH si es necesario
        if ! grep -q ".local/bin" "$USER_HOME/.bashrc"; then
            echo -e "${YELLOW}[INFO] Configurando PATH en ~/.bashrc${NC}"
            echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$USER_HOME/.bashrc"
        fi
    else
        echo -e "${RED}[ERROR] Falló la instalación de dependencias${NC}"
        exit 1
    fi
    rm -f "$TEMP_FILE"
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

# Instalar KRCA
install_krca() {
    echo -e "${YELLOW}[INFO] Instalando KRCA...${NC}"
    
    curl -sSL $SCRIPT_URL | sudo tee /usr/local/bin/kubectl-resource-container-audit.py >/dev/null
    sudo chmod +x /usr/local/bin/kubectl-resource-container-audit.py
    sudo ln -sf /usr/local/bin/kubectl-resource-container-audit.py /usr/local/bin/kubectl-krca
    
    echo -e "${GREEN}[SUCCESS] KRCA instalado correctamente${NC}"
}

# Verificaciones
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}[ERROR] Este script debe ejecutarse como root/sudo${NC}"
    exit 1
fi

# Proceso de instalación
echo -e "${GREEN}=== Instalador KRCA v5.1 ===${NC}"

install_wkhtmltopdf
install_python_deps
install_krca

echo -e "\n${GREEN}[SUCCESS] Instalación completada!${NC}"
echo -e "Usar con: ${YELLOW}kubectl krca --help${NC}"
echo -e "Nota: Puede necesitar ejecutar 'source ~/.bashrc' o abrir una nueva terminal"
