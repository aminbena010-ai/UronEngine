#!/bin/bash
# URON Engine - Instalación con estilo y colores

# --- Configuración de colores ANSI ---
RESET='\033[0m'
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

# --- Arte ASCII de bienvenida ---
echo -e "${CYAN}${BOLD}"
echo "  _   _  ____   ___  _   _ "
echo " | | | ||  _ \ / _ \| \ | |"
echo " | | | || |_) | | | |  \| |"
echo " | |_| ||  _ <| |_| | |\  |"
echo "  \___/ |_| \_\\___/|_| \_|"
echo -e "       E N G I N E${RESET}\n"
echo -e "${BLUE}==============================================${RESET}"
echo -e "${BOLD} 🛠️  Iniciando instalación del entorno URON...${RESET}"
echo -e "${BLUE}==============================================${RESET}\n"

# Ir a la raíz del proyecto
cd "$(dirname "$0")/.." || { echo -e "${RED}❌ Error: No se pudo encontrar la raíz del proyecto.${RESET}"; exit 1; }

# 1. Comprobar dependencias del sistema (uv)
echo -e "${YELLOW}[1/3] Comprobando instalador de paquetes (uv)...${RESET}"
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ 'uv' no está instalado.${RESET}"
    echo -e "   Por favor, instálalo con el siguiente comando:"
    echo -e "   ${CYAN}curl -LsSf https://astral.sh/uv/install.sh | sh${RESET}"
    exit 1
fi
echo -e "${GREEN}✅ uv detectado.${RESET}\n"

# 2. Crear entorno virtual
echo -e "${YELLOW}[2/3] Configurando entorno virtual (.venv)...${RESET}"
if [ ! -d ".venv" ]; then
    echo "   Creando un nuevo entorno en .venv..."
    uv venv
    echo -e "${GREEN}✅ Entorno virtual creado.${RESET}"
else
    echo -e "${GREEN}✅ El entorno virtual ya existe.${RESET}"
fi
echo ""

# 3. Instalar dependencias
echo -e "${YELLOW}[3/3] Instalando librerías (PyQt6, Pygame, OpenGL, etc.)...${RESET}"
uv pip install -r script/requirements.txt

echo -e "\n${GREEN}${BOLD}==============================================${RESET}"
echo -e "${GREEN}${BOLD} 🎉 ¡URON Engine instalado con éxito!${RESET}"
echo -e "${GREEN}${BOLD}==============================================${RESET}"
echo -e "👉 Para arrancar el IDE, ejecuta: ${CYAN}./init.sh${RESET}\n"