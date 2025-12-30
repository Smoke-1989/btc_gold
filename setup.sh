#!/bin/bash

# BTC GOLD V2.4 Setup Script
# Configura automaticamente o ambiente para performance otimizada

set -e

echo "██████╗ ████████╗██╗██████╗ ███████╗"
echo "██╔══██╗╚══██╔══╝██║██╔══██╗██╔════╝"
echo "██████╔╝   ██║   ██║██║  ██║██║  ███╗"
echo "██╔══██╗   ██║   ██║██║  ██║██║   ██║"
echo "██████╔╝   ██║   ██║██████╔╝██████╗"
echo "╚═════╝    ╚═╝   ╚═╝╚═════╝ ╚═════╝"
echo ""
echo "BTC GOLD V2.4 - Setup Automatizado"
echo "==================================="
echo ""

# Detectar OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
    echo "[*] SO: Linux ($DISTRO)"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    echo "[*] SO: macOS"
else
    echo "[ERROR] SO nao suportado: $OSTYPE"
    exit 1
fi

echo ""
echo "[*] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 nao encontrado. Instale: brew install python3 (macOS) ou apt install python3 (Linux)"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "[OK] Python $PYTHON_VERSION encontrado"

echo ""
echo "[*] Criando virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[OK] venv criado"
else
    echo "[OK] venv ja existe"
fi

echo ""
echo "[*] Ativando venv..."
source venv/bin/activate

echo ""
echo "[*] Atualizando pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "[OK] pip atualizado"

echo ""
echo "[*] Instalando dependencias criticas..."
pip install -r requirements.txt
echo "[OK] Dependencias instaladas"

echo ""
echo "[*] Configurando Numba JIT (OPCIONAL - 2-5x boost)..."
echo ""
echo "Deseja instalar Numba JIT? (Recomendado)"
echo "[1] Sim (recomendado para +2-5x performance)"
echo "[2] Nao (continuar sem otimizacao)"
read -p "Escolha [1/2]: " NUMBA_CHOICE

if [ "$NUMBA_CHOICE" = "1" ]; then
    echo ""
    echo "[*] Instalando LLVM (pode demorar)..."
    
    if [ "$OS" = "Linux" ]; then
        if command -v apt &> /dev/null; then
            echo "[*] Detectado Debian/Ubuntu"
            sudo apt-get update
            sudo apt-get install -y llvm-14 clang-14 > /dev/null 2>&1
            echo "[OK] LLVM instalado"
        elif command -v yum &> /dev/null; then
            echo "[*] Detectado RedHat/CentOS"
            sudo yum install -y llvm-devel > /dev/null 2>&1
            echo "[OK] LLVM instalado"
        else
            echo "[WARNING] Package manager nao reconhecido. Instale LLVM manualmente."
        fi
    elif [ "$OS" = "macOS" ]; then
        if ! command -v brew &> /dev/null; then
            echo "[ERROR] Homebrew nao encontrado. Instale em: https://brew.sh"
            exit 1
        fi
        echo "[*] Instalando LLVM via Homebrew..."
        brew install llvm@14 > /dev/null 2>&1
        echo "[OK] LLVM instalado"
    fi
    
    echo "[*] Instalando Numba..."
    pip install numba==0.59.1
    echo "[OK] Numba instalado"
    
    # Verificar
    if python3 -c "from numba import njit" 2>/dev/null; then
        echo "[OK] Numba JIT ativado com sucesso!"
    else
        echo "[WARNING] Numba nao funcionou. Continuando sem."
    fi
else
    echo "[SKIP] Numba ignorado. Performance sera limitada por Python."
fi

echo ""
echo "[*] Verificando dependencias criptograficas..."
if python3 -c "from coincurve import PrivateKey" 2>/dev/null; then
    echo "[OK] coincurve OK"
else
    echo "[ERROR] coincurve falhou"
    exit 1
fi

if python3 -c "import base58" 2>/dev/null; then
    echo "[OK] base58 OK"
else
    echo "[ERROR] base58 falhou"
    exit 1
fi

echo ""
echo "[*] Rodando benchmark inicial..."
echo ""
python3 benchmark.py

echo ""
echo "=============================================="
echo "[OK] Setup completo!"
echo "=============================================="
echo ""
echo "Proximos passos:"
echo ""
echo "1. Preencha alvos.txt com seus dados"
echo "   - Formato: Enderecos, HASH160 ou Public Keys"
echo ""
echo "2. Execute o programa:"
echo "   source venv/bin/activate"
echo "   python3 btc_gold.py"
echo ""
echo "3. Se quiser versao C++ otimizada:"
echo "   - Preencha HARDWARE_INFO_TEMPLATE.md"
echo "   - Compartilhe comigo"
echo ""
echo "Status: Pronto para mega performance! 🚀"
