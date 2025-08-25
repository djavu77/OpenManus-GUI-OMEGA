#!/bin/bash

# Script de Instalação de Pré-requisitos
# Sistema de IA Conversacional Avançada - OpenManus

set -e

echo "🚀 Iniciando instalação dos pré-requisitos..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se está rodando como root
if [[ $EUID -eq 0 ]]; then
   log_error "Este script não deve ser executado como root"
   exit 1
fi

# Detectar sistema operacional
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    log_error "Sistema operacional não suportado: $OSTYPE"
    exit 1
fi

log_info "Sistema detectado: $OS"

# Função para verificar se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Instalar Python 3.12
install_python() {
    log_info "Verificando instalação do Python 3.12..."
    
    if command_exists python3.12; then
        log_success "Python 3.12 já está instalado"
        return
    fi
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ "$PYTHON_VERSION" == "3.12" ]]; then
            log_success "Python 3.12 já está instalado como python3"
            return
        fi
    fi
    
    log_info "Instalando Python 3.12..."
    
    case $OS in
        "linux")
            if [[ "$DISTRO" == "Ubuntu" ]] || [[ "$DISTRO" == "Debian" ]]; then
                sudo apt update
                sudo apt install -y software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt update
                sudo apt install -y python3.12 python3.12-venv python3.12-pip
            elif [[ "$DISTRO" == "CentOS" ]] || [[ "$DISTRO" == "RedHat" ]]; then
                sudo yum install -y python3.12 python3.12-pip
            else
                log_warning "Distribuição Linux não reconhecida. Tentando instalação genérica..."
                sudo apt update && sudo apt install -y python3.12 python3.12-venv python3.12-pip
            fi
            ;;
        "macos")
            if command_exists brew; then
                brew install python@3.12
            else
                log_error "Homebrew não encontrado. Instale o Homebrew primeiro: https://brew.sh"
                exit 1
            fi
            ;;
        "windows")
            log_error "Para Windows, baixe e instale Python 3.12 de: https://www.python.org/downloads/"
            exit 1
            ;;
    esac
    
    log_success "Python 3.12 instalado com sucesso"
}

# Instalar Node.js e npm
install_nodejs() {
    log_info "Verificando instalação do Node.js..."
    
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
        if [[ $NODE_VERSION -ge 18 ]]; then
            log_success "Node.js $(node --version) já está instalado"
            return
        fi
    fi
    
    log_info "Instalando Node.js 20..."
    
    case $OS in
        "linux")
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt-get install -y nodejs
            ;;
        "macos")
            if command_exists brew; then
                brew install node@20
            else
                log_error "Homebrew não encontrado"
                exit 1
            fi
            ;;
        "windows")
            log_error "Para Windows, baixe Node.js de: https://nodejs.org"
            exit 1
            ;;
    esac
    
    log_success "Node.js instalado com sucesso"
}

# Instalar Docker
install_docker() {
    log_info "Verificando instalação do Docker..."
    
    if command_exists docker; then
        log_success "Docker já está instalado"
        return
    fi
    
    log_info "Instalando Docker..."
    
    case $OS in
        "linux")
            curl -fsSL https://get.docker.com -o get-docker.sh
            sudo sh get-docker.sh
            sudo usermod -aG docker $USER
            rm get-docker.sh
            ;;
        "macos")
            log_warning "Para macOS, baixe Docker Desktop de: https://www.docker.com/products/docker-desktop"
            ;;
        "windows")
            log_warning "Para Windows, baixe Docker Desktop de: https://www.docker.com/products/docker-desktop"
            ;;
    esac
    
    log_success "Docker instalado com sucesso"
}

# Instalar PostgreSQL
install_postgresql() {
    log_info "Verificando instalação do PostgreSQL..."
    
    if command_exists psql; then
        log_success "PostgreSQL já está instalado"
        return
    fi
    
    log_info "Instalando PostgreSQL..."
    
    case $OS in
        "linux")
            if [[ "$DISTRO" == "Ubuntu" ]] || [[ "$DISTRO" == "Debian" ]]; then
                sudo apt update
                sudo apt install -y postgresql postgresql-contrib
                sudo systemctl start postgresql
                sudo systemctl enable postgresql
            fi
            ;;
        "macos")
            if command_exists brew; then
                brew install postgresql@15
                brew services start postgresql@15
            fi
            ;;
    esac
    
    log_success "PostgreSQL instalado com sucesso"
}

# Instalar Redis
install_redis() {
    log_info "Verificando instalação do Redis..."
    
    if command_exists redis-server; then
        log_success "Redis já está instalado"
        return
    fi
    
    log_info "Instalando Redis..."
    
    case $OS in
        "linux")
            sudo apt update
            sudo apt install -y redis-server
            sudo systemctl start redis-server
            sudo systemctl enable redis-server
            ;;
        "macos")
            if command_exists brew; then
                brew install redis
                brew services start redis
            fi
            ;;
    esac
    
    log_success "Redis instalado com sucesso"
}

# Instalar Ollama
install_ollama() {
    log_info "Verificando instalação do Ollama..."
    
    if command_exists ollama; then
        log_success "Ollama já está instalado"
    else
        log_info "Instalando Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        log_success "Ollama instalado com sucesso"
    fi
    
    # Iniciar Ollama em background
    log_info "Iniciando Ollama..."
    ollama serve &
    sleep 5
    
    # Baixar modelo TeenyTinyLlama
    log_info "Baixando modelo TeenyTinyLlama..."
    ollama pull tinyllama
    
    log_success "TeenyTinyLlama baixado com sucesso"
}

# Verificar instalações
verify_installations() {
    log_info "Verificando instalações..."
    
    local errors=0
    
    # Verificar Python
    if command_exists python3.12 || (command_exists python3 && [[ $(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2) == "3.12" ]]); then
        log_success "✓ Python 3.12"
    else
        log_error "✗ Python 3.12"
        ((errors++))
    fi
    
    # Verificar Node.js
    if command_exists node && [[ $(node --version | cut -d'v' -f2 | cut -d'.' -f1) -ge 18 ]]; then
        log_success "✓ Node.js $(node --version)"
    else
        log_error "✗ Node.js 18+"
        ((errors++))
    fi
    
    # Verificar Docker
    if command_exists docker; then
        log_success "✓ Docker"
    else
        log_error "✗ Docker"
        ((errors++))
    fi
    
    # Verificar PostgreSQL
    if command_exists psql; then
        log_success "✓ PostgreSQL"
    else
        log_error "✗ PostgreSQL"
        ((errors++))
    fi
    
    # Verificar Redis
    if command_exists redis-server; then
        log_success "✓ Redis"
    else
        log_error "✗ Redis"
        ((errors++))
    fi
    
    # Verificar Ollama
    if command_exists ollama; then
        log_success "✓ Ollama"
    else
        log_error "✗ Ollama"
        ((errors++))
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "🎉 Todos os pré-requisitos foram instalados com sucesso!"
        log_info "Próximo passo: Execute ./scripts/setup_openmanus.sh"
    else
        log_error "❌ $errors erro(s) encontrado(s). Verifique as instalações acima."
        exit 1
    fi
}

# Função principal
main() {
    log_info "=== Instalação de Pré-requisitos - Sistema IA Conversacional ==="
    
    install_python
    install_nodejs
    install_docker
    install_postgresql
    install_redis
    install_ollama
    
    verify_installations
}

# Executar função principal
main "$@"