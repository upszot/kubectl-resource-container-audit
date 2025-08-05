#!/bin/bash
# KRCA Installer v2 - Con gestión de dependencias Python

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

# Detección de distribución
detect_distro() {
    if [ -f /etc/redhat-release ]; then
        echo "rhel"
    elif [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
        echo "debian"
    else
        echo "unknown"
    fi
}

# Instalar dependencias del sistema
install_system_deps() {
    local distro=$1
    echo -e "${YELLOW}[INFO] Instalando dependencias del sistema para ${distro}...${NC}"

    case $distro in
        rhel)
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3-pip
            else
                sudo yum install -y python3-pip
            fi
            ;;
        debian)
            sudo apt-get update
            sudo apt-get install -y python3-pip python3-venv
            ;;
        *)
            echo -e "${RED}[ERROR] Distribución no soportada${NC}"
            exit 1
            ;;
    esac
}

# Instalar wkhtmltopdf
install_wkhtmltopdf() {
    if ! command -v wkhtmltopdf &> /dev/null; then
        echo -e "${YELLOW}[INFO] Instalando wkhtmltopdf...${NC}"
        
        case $(detect_distro) in
            rhel)
                sudo yum install -y xorg-x11-fonts-75dpi xorg-x11-fonts-Type1
                sudo rpm -Uvh https://downloads.wkhtmltopdf.org/0.12/0.12.5/wkhtmltox-0.12.5-1.centos7.x86_64.rpm
                ;;
            debian)
                sudo apt-get install -y xfonts-75dpi xfonts-base
                wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.$(lsb_release -sc)_amd64.deb
                sudo dpkg -i wkhtmltox_*.deb
                sudo apt-get -f install -y
                rm wkhtmltox_*.deb
                ;;
        esac
    fi
}

# Instalar dependencias Python
install_python_deps() {
    echo -e "${YELLOW}[INFO] Instalando dependencias Python...${NC}"
    
    # Crear directorio temporal
    TEMP_DIR=$(mktemp -d)
    REQUIREMENTS_FILE="$TEMP_DIR/requirements.txt"
    
    # Descargar requirements.txt
    if ! curl -sSL $REQUIREMENTS_URL -o $REQUIREMENTS_FILE; then
        echo -e "${RED}[ERROR] No se pudo descargar requirements.txt${NC}"
        exit 1
    fi

    # Instalar dependencias
    pip3 install --user -r $REQUIREMENTS_FILE
    
    # Limpiar
    rm -rf $TEMP_DIR
}

# Instalar KRCA
install_krca() {
    echo -e "${YELLOW}[INFO] Instalando KRCA...${NC}"
    
    sudo curl -sSL $SCRIPT_URL -o /usr/local/bin/kubectl-resource-container-audit.py
    sudo chmod +x /usr/local/bin/kubectl-resource-container-audit.py
    sudo ln -sf /usr/local/bin/kubectl-resource-container-audit.py /usr/local/bin/kubectl-krca
}

# Verificaciones iniciales
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}[ERROR] Este script debe ejecutarse como root/sudo${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 no está instalado${NC}"
    exit 1
fi

# Proceso de instalación
echo -e "${GREEN}=== Instalador KRCA ===${NC}"
DISTRO=$(detect_distro)

install_system_deps $DISTRO
install_wkhtmltopdf
install_python_deps
install_krca

echo -e "\n${GREEN}[SUCCESS] Instalación completada correctamente!${NC}"
echo -e "Usar con: ${YELLOW}kubectl krca --help${NC}"

