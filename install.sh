#!/bin/bash
# =============================================================================
# install.sh - Instalador automatico do Controlador de Gastos para Ubuntu
# =============================================================================
# Este script configura tudo automaticamente:
#   - Virtualenv com acesso ao sistema (para GTK/WebKit funcionar)
#   - Instala pywebview
#   - Cria o launcher run.sh
#   - Cria o icone do app
#   - Registra o app no menu do Ubuntu
#
# Como usar:
#   cd ~/Meus-Projetos/Controlador-Gastos
#   chmod +x install.sh
#   ./install.sh
# =============================================================================

set -e  # Para em qualquer erro

# Cores para output
VERDE='\033[0;32m'
AMARELO='\033[1;33m'
VERMELHO='\033[0;31m'
NC='\033[0m' # No Color

# Detecta o diretorio do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="$HOME"
VENV_DIR="$USER_HOME/meu_env"
APP_NAME="Controlador de Gastos"
DESKTOP_FILE="$USER_HOME/.local/share/applications/Controlador-de-Gastos.desktop"

echo "=========================================="
echo "  Instalador - Controlador de Gastos"
echo "=========================================="
echo ""

# -----------------------------------------------------------------------------
# 1. Verificar dependencias do sistema
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[1/6] Verificando dependencias do sistema...${NC}"

MISSING=()
for pkg in python3 python3-venv python3-pip python3-gi gir1.2-gtk-3.0 webkit2gtk-4.0; do
    if ! dpkg -l "$pkg" &>/dev/null; then
        MISSING+=("$pkg")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${AMARELO}    Pacotes faltando: ${MISSING[*]}${NC}"
    echo -e "${AMARELO}    Instalando...${NC}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${MISSING[@]}"
else
    echo -e "${VERDE}    Todas as dependencias estao instaladas.${NC}"
fi

# -----------------------------------------------------------------------------
# 2. Criar virtualenv
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[2/6] Configurando ambiente Python...${NC}"

if [ ! -d "$VENV_DIR" ]; then
    echo "    Criando virtualenv em $VENV_DIR ..."
    python3 -m venv "$VENV_DIR" --system-site-packages
    echo -e "${VERDE}    Virtualenv criado com sucesso.${NC}"
else
    echo -e "${VERDE}    Virtualenv ja existe em $VENV_DIR${NC}"
fi

# -----------------------------------------------------------------------------
# 3. Instalar pywebview
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[3/6] Instalando pywebview...${NC}"
source "$VENV_DIR/bin/activate"
pip install -q pywebview
echo -e "${VERDE}    pywebview instalado.${NC}"

# -----------------------------------------------------------------------------
# 4. Criar o script de execucao (run.sh)
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[4/6] Criando launcher run.sh...${NC}"

cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
# Launcher automatico do Controlador de Gastos
# Ativa o virtualenv e executa o app

source "$HOME/meu_env/bin/activate"
cd "$(dirname "$(readlink -f "$0")")"
python3 app.py
EOF

chmod +x "$SCRIPT_DIR/run.sh"
echo -e "${VERDE}    run.sh criado em $SCRIPT_DIR/run.sh${NC}"

# -----------------------------------------------------------------------------
# 5. Criar o icone
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[5/6] Criando icone do app...${NC}"

cat > "$SCRIPT_DIR/icon.svg" << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="128" height="128">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#059669;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="100" height="100" rx="20" fill="url(#grad)"/>
  <circle cx="50" cy="45" r="22" fill="none" stroke="white" stroke-width="4"/>
  <text x="50" y="52" font-size="28" text-anchor="middle" fill="white" font-family="sans-serif" font-weight="bold">R$</text>
  <rect x="28" y="68" width="44" height="6" rx="3" fill="white" opacity="0.8"/>
</svg>
EOF

echo -e "${VERDE}    Icone criado em $SCRIPT_DIR/icon.svg${NC}"

# -----------------------------------------------------------------------------
# 6. Criar o arquivo .desktop (registro no menu do Ubuntu)
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[6/6] Registrando app no menu do Ubuntu...${NC}"

mkdir -p "$USER_HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Name=Controlador de Gastos
Comment=Gerenciador financeiro pessoal com PyWebView
Exec=$SCRIPT_DIR/run.sh
Icon=$SCRIPT_DIR/icon.svg
Path=$SCRIPT_DIR
Type=Application
Terminal=false
Categories=Office;Finance;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

# Atualiza o cache de aplicativos
update-desktop-database "$USER_HOME/.local/share/applications/" 2>/dev/null || true

echo -e "${VERDE}    App registrado em $DESKTOP_FILE${NC}"

# -----------------------------------------------------------------------------
# FIM
# -----------------------------------------------------------------------------
echo ""
echo "=========================================="
echo -e "${VERDE}  Instalacao concluida com sucesso!${NC}"
echo "=========================================="
echo ""
echo "Como usar:"
echo "  1. Pressione a tecla SUPER (Windows)"
echo "  2. Digite: Controlador de Gastos"
echo "  3. Clique no icone para abrir"
echo ""
echo "Ou execute diretamente:"
echo "  $SCRIPT_DIR/run.sh"
echo ""
echo "Para fixar no dock:"
echo "  Abra o app, clique direito no icone -> 'Adicionar aos favoritos'"
echo ""
