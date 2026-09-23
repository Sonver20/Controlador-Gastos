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
#   cd ~/Meus-Projetos/Controlador-Gastos (Ajuste se não for onde quer)
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
VENV_DIR="$SCRIPT_DIR/.venv"
APP_NAME="Controlador de Gastos"
DESKTOP_FILE="$USER_HOME/.local/share/applications/Controlador-de-Gastos.desktop"
ICON_PATH="$SCRIPT_DIR/icons/icon.svg"

# Detecta o Python do sistema (evita snap que quebra GTK/WebKit)
PYTHON_BIN="$(which python3 2>/dev/null || true)"
PYTHON_REAL=""
if [ -n "$PYTHON_BIN" ]; then
    PYTHON_REAL="$(readlink -f "$PYTHON_BIN" 2>/dev/null || true)"
fi

# Se o python3 padrao for um snap, busca o do sistema
if [ -z "$PYTHON_REAL" ] || [[ "$PYTHON_REAL" == *"/snap/"* ]]; then
    if [ -x "/usr/bin/python3" ]; then
        PYTHON_BIN="/usr/bin/python3"
        PYTHON_REAL="$(readlink -f "$PYTHON_BIN" 2>/dev/null || true)"
    fi
fi

# Se ainda for snap ou nao existir, tenta outros caminhos
if [ -z "$PYTHON_REAL" ] || [[ "$PYTHON_REAL" == *"/snap/"* ]]; then
    for candidate in /usr/bin/python3 /usr/local/bin/python3; do
        if [ -x "$candidate" ]; then
            real="$(readlink -f "$candidate" 2>/dev/null || true)"
            if [ -n "$real" ] && [[ "$real" != *"/snap/"* ]]; then
                PYTHON_BIN="$candidate"
                PYTHON_REAL="$real"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
    echo -e "${VERMELHO}ERRO: Nao foi possivel encontrar um Python3 do sistema (nao-snap).${NC}"
    echo -e "${AMARELO}Instale com: sudo apt install python3 python3-venv python3-pip${NC}"
    exit 1
fi

echo -e "${VERDE}    Python detectado: $PYTHON_BIN ($PYTHON_REAL)${NC}"

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
    echo "    Criando virtualenv em $VENV_DIR com $PYTHON_BIN ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR" --system-site-packages
    echo -e "${VERDE}    Virtualenv criado com sucesso.${NC}"
else
    echo -e "${VERDE}    Virtualenv ja existe em $VENV_DIR${NC}"
fi

# -----------------------------------------------------------------------------
# 3. Instalar pywebview
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[3/6] Instalando pywebview...${NC}"
"$VENV_DIR/bin/pip" install -q pywebview
echo -e "${VERDE}    pywebview instalado.${NC}"

# -----------------------------------------------------------------------------
# 4. Criar o script de execucao (run.sh)
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[4/6] Criando launcher run.sh...${NC}"

cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
# Launcher automatico do Controlador de Gastos
# Usa o Python do venv diretamente (evita conflito com snap)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GTK_MODULES
unset GIO_MODULE_DIR GIO_LAUNCHED_DESKTOP_FILE
"$SCRIPT_DIR/.venv/bin/python3" app.py
EOF

chmod +x "$SCRIPT_DIR/run.sh"
echo -e "${VERDE}    run.sh criado em $SCRIPT_DIR/run.sh${NC}"

# -----------------------------------------------------------------------------
# 5. Verificar o icone
# -----------------------------------------------------------------------------
echo -e "${AMARELO}[5/6] Verificando icone do app...${NC}"
if [ ! -f "$ICON_PATH" ]; then
        echo -e "${VERMELHO}ERRO: Icone nao encontrado em $ICON_PATH${NC}"
        exit 1
fi
echo -e "${VERDE}    Icone encontrado em $ICON_PATH${NC}"

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
Icon=$ICON_PATH
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
