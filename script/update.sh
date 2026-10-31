#!/bin/bash
# URON Engine - Actualización y limpieza

RESET='\033[0m'
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

# --- Arte ASCII ---
echo -e "${CYAN}${BOLD}"
echo "  _   _  ____   ___  _   _ "
echo " | | | ||  _ \ / _ \| \ | |"
echo " | | | || |_) | | | |  \| |"
echo " | |_| ||  _ <| |_| | |\  |"
echo "  \___/ |_| \_\\___/|_| \_|"
echo -e "       E N G I N E${RESET}\n"

echo -e "${BLUE}==============================================${RESET}"
echo -e "${BOLD} 🔄 Actualizando dependencias de URON...${RESET}"
echo -e "${BLUE}==============================================${RESET}\n"

cd "$(dirname "$0")/.." || { echo -e "${RED}❌ Error: No se pudo encontrar la raíz del proyecto.${RESET}"; exit 1; }

if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ No se encontró el entorno virtual.${RESET}"
    echo -e "   Ejecuta primero: ${CYAN}./script/install.sh${RESET}"
    exit 1
fi

echo -e "${YELLOW}[1/2] Actualizando paquetes...${RESET}"
uv pip install --upgrade -r script/requirements.txt
echo -e "${GREEN}✅ Paquetes actualizados.${RESET}\n"

echo -e "${YELLOW}[2/2] Limpiando caché de Python (__pycache__)...${RESET}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo -e "${GREEN}✅ Caché limpia.${RESET}\n"

echo -e "${GREEN}${BOLD}==============================================${RESET}"
echo -e "${GREEN}${BOLD} 🎉 ¡URON Engine actualizado!${RESET}"
echo -e "${GREEN}${BOLD}==============================================${RESET}\n"