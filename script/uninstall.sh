#!/bin/bash
# URON Engine - Desinstalación segura

RESET='\033[0m'
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'

echo -e "${CYAN}${BOLD}"
echo "  _   _  ____   ___  _   _ "
echo " | | | ||  _ \ / _ \| \ | |"
echo " | | | || |_) | | | |  \| |"
echo " | |_| ||  _ <| |_| | |\  |"
echo "  \___/ |_| \_\\___/|_| \_|"
echo -e "       E N G I N E${RESET}\n"

echo -e "${RED}${BOLD}==============================================${RESET}"
echo -e "${RED}${BOLD} ⚠️  ADVERTENCIA DE DESINSTALACIÓN${RESET}"
echo -e "${RED}${BOLD}==============================================${RESET}"
echo -e "Esto eliminará el entorno virtual (.venv) y la caché."
echo -e "Tus proyectos (carpeta MiJuego, etc.) ${BOLD}NO${RESET} se borrarán."
echo ""
read -p "$(echo -e ${YELLOW}¿Estás seguro de que quieres desinstalar URON? [s/N]: ${RESET})" confirm

if [[ "$confirm" != "s" && "$confirm" != "S" ]]; then
    echo -e "\n${GREEN}✅ Desinstalación cancelada. URON sigue intacto.${RESET}\n"
    exit 0
fi

cd "$(dirname "$0")/.." || { echo -e "${RED}❌ Error: No se pudo encontrar la raíz del proyecto.${RESET}"; exit 1; }

echo -e "\n${YELLOW}[1/2] Eliminando entorno virtual (.venv)...${RESET}"
if [ -d ".venv" ]; then
    rm -rf .venv
    echo -e "${GREEN}✅ Entorno virtual eliminado.${RESET}"
else
    echo -e "${YELLOW}⚠️  No se encontró el entorno virtual.${RESET}"
fi

echo -e "\n${YELLOW}[2/2] Limpiando archivos __pycache__...${RESET}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo -e "${GREEN}✅ Caché limpia.${RESET}"

echo -e "\n${GREEN}${BOLD}==============================================${RESET}"
echo -e "${GREEN}${BOLD} 🎉 URON Engine desinstalado.${RESET}"
echo -e "${GREEN}${BOLD}==============================================${RESET}"
echo -e "👉 Para volver a instalar, ejecuta: ${CYAN}./script/install.sh${RESET}\n"