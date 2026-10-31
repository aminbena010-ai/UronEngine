#!/bin/bash
# URON Engine - Iniciar IDE con comprobaciones y color

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
echo -e "${BOLD} 🚀 Arrancando el entorno de desarrollo...${RESET}"
echo -e "${BLUE}==============================================${RESET}\n"

# Comprobar si existe el entorno virtual
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ No se encontró el entorno virtual (.venv).${RESET}"
    echo -e "   Por favor, ejecuta primero: ${CYAN}./script/install.sh${RESET}"
    exit 1
fi

echo -e "${YELLOW}⏳ Iniciando URON IDE...${RESET}"

# Arrancar el IDE usando uv
uv run python main.py "$@"

# Capturar el código de salida del IDE
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ URON Engine cerrado correctamente.${RESET}"
else
    echo -e "\n${RED}⚠️  El IDE se cerró con errores (código $EXIT_CODE).${RESET}"
fi