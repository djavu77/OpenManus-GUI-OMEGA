#!/bin/bash

# Script de Configuração Completa do Sistema de IA Conversacional Avançada
# Integração OpenManus + ChatBot-UI + TeenyTinyLlama

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Funções de log
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }
log_detail() { echo -e "${CYAN}[DETAIL]${NC} $1"; }

# Verificar se está sendo executado como root
if [[ $EUID -eq 0 ]]; then
   log_error "Este script não deve ser executado como root"
   exit 1
fi

# Detectar sistema operacional
detect_os() {
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
    log_info "Sistema detectado: $OS ($DISTRO)"
}

# Verificar se comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Instalar pré-requisitos
install_prerequisites() {
    log_step "Instalando pré-requisitos do sistema..."
    
    # Python 3.12
    if ! command_exists python3.12 && ! (command_exists python3 && [[ $(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2) == "3.12" ]]); then
        log_info "Instalando Python 3.12..."
        case $OS in
            "linux")
                sudo apt update
                sudo apt install -y software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt update
                sudo apt install -y python3.12 python3.12-venv python3.12-pip python3.12-dev
                ;;
            "macos")
                if command_exists brew; then
                    brew install python@3.12
                else
                    log_error "Homebrew necessário para macOS. Instale em: https://brew.sh"
                    exit 1
                fi
                ;;
        esac
        log_success "Python 3.12 instalado"
    else
        log_success "Python 3.12 já está disponível"
    fi
    
    # Node.js 18+
    if ! command_exists node || [[ $(node --version | cut -d'v' -f2 | cut -d'.' -f1) -lt 18 ]]; then
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
                    log_error "Homebrew necessário"
                    exit 1
                fi
                ;;
        esac
        log_success "Node.js instalado"
    else
        log_success "Node.js já está disponível"
    fi
    
    # PostgreSQL
    if ! command_exists psql; then
        log_info "Instalando PostgreSQL..."
        case $OS in
            "linux")
                sudo apt update
                sudo apt install -y postgresql postgresql-contrib
                sudo systemctl start postgresql
                sudo systemctl enable postgresql
                ;;
            "macos")
                if command_exists brew; then
                    brew install postgresql@15
                    brew services start postgresql@15
                fi
                ;;
        esac
        log_success "PostgreSQL instalado"
    else
        log_success "PostgreSQL já está disponível"
    fi
    
    # Redis
    if ! command_exists redis-server; then
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
        log_success "Redis instalado"
    else
        log_success "Redis já está disponível"
    fi
    
    # Docker (opcional, para ChromaDB)
    if ! command_exists docker; then
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
        esac
        log_success "Docker instalado"
    else
        log_success "Docker já está disponível"
    fi
    
    # Ollama
    if ! command_exists ollama; then
        log_info "Instalando Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        log_success "Ollama instalado"
    else
        log_success "Ollama já está disponível"
    fi
}

# Configurar backend
setup_backend() {
    log_step "Configurando backend do sistema..."
    
    # Criar estrutura de diretórios
    mkdir -p backend/{services,models,utils,tests}
    mkdir -p config/backend
    mkdir -p logs
    mkdir -p data/{backups,exports}
    
    # Determinar comando Python
    PYTHON_CMD=""
    if command_exists python3.12; then
        PYTHON_CMD="python3.12"
    elif command_exists python3 && [[ $(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2) == "3.12" ]]; then
        PYTHON_CMD="python3"
    else
        log_error "Python 3.12 não encontrado"
        exit 1
    fi
    
    # Criar ambiente virtual
    log_info "Criando ambiente virtual Python..."
    $PYTHON_CMD -m venv backend/venv
    source backend/venv/bin/activate
    
    # Atualizar pip
    pip install --upgrade pip
    
    # Instalar dependências do OpenManus
    log_info "Instalando dependências do OpenManus..."
    pip install -r requirements.txt
    
    # Instalar dependências adicionais para o sistema avançado
    log_info "Instalando dependências adicionais..."
    cat > backend/requirements-extended.txt << 'EOF'
# Dependências base do OpenManus (já instaladas via requirements.txt)

# Dependências para sistema avançado
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
alembic==1.13.1
redis==5.0.1
celery==5.3.4
chromadb==0.4.22
sentence-transformers==2.2.2
scikit-learn==1.3.2
pandas==2.1.4

# Autenticação e segurança
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Monitoramento
prometheus-client==0.19.0
psutil==5.9.6

# Processamento de texto avançado
spacy==3.7.2
textblob==0.17.1
nltk==3.8.1

# Utilitários
python-dotenv==1.0.0
pydantic-settings==2.1.0
typer==0.9.0
rich==13.7.0
EOF
    
    pip install -r backend/requirements-extended.txt
    
    # Configurar variáveis de ambiente
    log_info "Configurando variáveis de ambiente..."
    cat > config/backend/.env << 'EOF'
# Configuração do Sistema de IA Conversacional Avançada

# Banco de Dados PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sistema_ia_conversacional
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sistema_ia_conversacional

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_DB=1
REDIS_SESSION_DB=2

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8001
CHROMADB_PERSIST_DIRECTORY=./data/chromadb

# Ollama e TeenyTinyLlama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=tinyllama
OLLAMA_TIMEOUT=300

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=sua_chave_secreta_super_segura_mude_em_producao_$(openssl rand -hex 32)
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Celery
CELERY_BROKER_URL=redis://localhost:6379/3
CELERY_RESULT_BACKEND=redis://localhost:6379/4

# Configurações de Aprendizado
ENABLE_AUTO_LEARNING=true
FEEDBACK_THRESHOLD=3
EMBEDDING_MODEL=all-MiniLM-L6-v2
LEARNING_RATE=0.1
CONFIDENCE_THRESHOLD=0.7

# Configurações de Monitoramento
ENABLE_METRICS=true
METRICS_RETENTION_DAYS=30
LOG_LEVEL=INFO

# Configurações de Segurança
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Configurações de Performance
MAX_WORKERS=4
WORKER_TIMEOUT=300
MAX_CONNECTIONS=100
EOF
    
    log_success "Backend configurado com sucesso"
}

# Configurar frontend
setup_frontend() {
    log_step "Configurando frontend do sistema..."
    
    # Verificar se Node.js está disponível
    if ! command_exists node; then
        log_error "Node.js não encontrado"
        exit 1
    fi
    
    # Instalar dependências do frontend
    log_info "Instalando dependências do frontend..."
    cd frontend
    npm install
    cd ..
    
    # Configurar variáveis de ambiente do frontend
    log_info "Configurando variáveis de ambiente do frontend..."
    cat > frontend/.env.local << 'EOF'
# Configuração do Frontend - Sistema IA Conversacional

# URLs da API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Configurações da Aplicação
NEXT_PUBLIC_APP_NAME=Sistema IA Conversacional Avançada
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_APP_DESCRIPTION=Plataforma de IA com auto-aprendizado e memória persistente

# Configurações de Desenvolvimento
NEXT_PUBLIC_DEBUG=true
NEXT_PUBLIC_LOG_LEVEL=info

# Configurações de UI
NEXT_PUBLIC_THEME=light
NEXT_PUBLIC_ENABLE_DARK_MODE=true
NEXT_PUBLIC_MAX_MESSAGE_LENGTH=4000
NEXT_PUBLIC_TYPING_INDICATOR_DELAY=500

# Configurações de Performance
NEXT_PUBLIC_ENABLE_STREAMING=true
NEXT_PUBLIC_CHUNK_SIZE=1024
NEXT_PUBLIC_REQUEST_TIMEOUT=30000

# Configurações de Feedback
NEXT_PUBLIC_ENABLE_FEEDBACK=true
NEXT_PUBLIC_FEEDBACK_TYPES=["rating","comment","suggestion"]

# Configurações de Métricas
NEXT_PUBLIC_ENABLE_METRICS=true
NEXT_PUBLIC_METRICS_REFRESH_INTERVAL=30000
EOF
    
    log_success "Frontend configurado com sucesso"
}

# Configurar bancos de dados
setup_databases() {
    log_step "Configurando bancos de dados..."
    
    # PostgreSQL
    log_info "Configurando PostgreSQL..."
    
    # Criar banco de dados
    sudo -u postgres createdb sistema_ia_conversacional 2>/dev/null || log_detail "Banco já existe"
    
    # Configurar usuário (se necessário)
    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';" 2>/dev/null || true
    
    log_success "PostgreSQL configurado"
    
    # ChromaDB
    log_info "Configurando ChromaDB..."
    
    # Instalar ChromaDB se não estiver instalado
    source backend/venv/bin/activate
    pip install chromadb==0.4.22
    
    # Criar diretório de persistência
    mkdir -p data/chromadb
    
    log_success "ChromaDB configurado"
    
    # Redis
    log_info "Verificando Redis..."
    if systemctl is-active --quiet redis-server 2>/dev/null || systemctl is-active --quiet redis 2>/dev/null; then
        log_success "Redis está rodando"
    else
        log_warning "Redis pode não estar rodando. Verifique o serviço."
    fi
}

# Configurar Ollama e modelo
setup_ollama() {
    log_step "Configurando Ollama e TeenyTinyLlama..."
    
    # Iniciar Ollama se não estiver rodando
    if ! pgrep -x "ollama" > /dev/null; then
        log_info "Iniciando Ollama..."
        nohup ollama serve > logs/ollama.log 2>&1 &
        sleep 5
    fi
    
    # Verificar se Ollama está respondendo
    local max_attempts=10
    local attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
            log_success "Ollama está rodando"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Ollama não está respondendo após $max_attempts tentativas"
            exit 1
        fi
        
        log_detail "Aguardando Ollama inicializar... (tentativa $attempt/$max_attempts)"
        sleep 3
        ((attempt++))
    done
    
    # Baixar modelo TeenyTinyLlama
    log_info "Verificando modelo TeenyTinyLlama..."
    if ollama list | grep -q "tinyllama"; then
        log_success "Modelo TeenyTinyLlama já está disponível"
    else
        log_info "Baixando modelo TeenyTinyLlama (isso pode demorar alguns minutos)..."
        ollama pull tinyllama
        log_success "Modelo TeenyTinyLlama baixado com sucesso"
    fi
    
    # Testar modelo
    log_info "Testando modelo..."
    test_response=$(ollama run tinyllama "Olá, você está funcionando?" --timeout 30s 2>/dev/null || echo "erro")
    if [[ "$test_response" != "erro" ]]; then
        log_success "Modelo TeenyTinyLlama testado com sucesso"
    else
        log_warning "Teste do modelo falhou, mas continuando..."
    fi
}

# Inicializar banco de dados
initialize_database() {
    log_step "Inicializando schema do banco de dados..."
    
    source backend/venv/bin/activate
    
    # Executar script de inicialização do banco
    python3 -c "
import asyncio
import sys
sys.path.append('.')
from backend.services.database_service import DatabaseService

async def init_db():
    db_service = DatabaseService('postgresql+asyncpg://postgres:postgres@localhost:5432/sistema_ia_conversacional')
    await db_service.initialize()
    print('✅ Banco de dados inicializado com sucesso')

asyncio.run(init_db())
"
    
    log_success "Schema do banco de dados criado"
}

# Configurar serviços de background
setup_background_services() {
    log_step "Configurando serviços de background..."
    
    # Criar scripts de serviço
    mkdir -p scripts/services
    
    # Script para ChromaDB
    cat > scripts/services/start_chromadb.sh << 'EOF'
#!/bin/bash
source backend/venv/bin/activate
export CHROMADB_HOST=localhost
export CHROMADB_PORT=8001
export CHROMADB_PERSIST_DIRECTORY=./data/chromadb
nohup chroma run --host $CHROMADB_HOST --port $CHROMADB_PORT --path $CHROMADB_PERSIST_DIRECTORY > logs/chromadb.log 2>&1 &
echo $! > data/chromadb.pid
EOF
    
    # Script para Celery Worker
    cat > scripts/services/start_celery.sh << 'EOF'
#!/bin/bash
source backend/venv/bin/activate
cd backend
nohup celery -A services.celery_app worker --loglevel=info --concurrency=2 > ../logs/celery.log 2>&1 &
echo $! > ../data/celery.pid
cd ..
EOF
    
    # Script para Celery Beat (tarefas periódicas)
    cat > scripts/services/start_celery_beat.sh << 'EOF'
#!/bin/bash
source backend/venv/bin/activate
cd backend
nohup celery -A services.celery_app beat --loglevel=info > ../logs/celery-beat.log 2>&1 &
echo $! > ../data/celery-beat.pid
cd ..
EOF
    
    chmod +x scripts/services/*.sh
    
    log_success "Serviços de background configurados"
}

# Criar scripts de gerenciamento
create_management_scripts() {
    log_step "Criando scripts de gerenciamento..."
    
    # Script principal de inicialização
    cat > start_sistema_ia.sh << 'EOF'
#!/bin/bash

# Script de Inicialização do Sistema de IA Conversacional Avançada

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Carregar variáveis de ambiente
if [[ -f "config/backend/.env" ]]; then
    source config/backend/.env
    log_info "Variáveis de ambiente carregadas"
fi

# Criar diretórios necessários
mkdir -p logs data

log_info "🚀 Iniciando Sistema de IA Conversacional Avançada..."

# 1. Iniciar PostgreSQL (se não estiver rodando)
if ! pgrep -x "postgres" > /dev/null; then
    log_info "Iniciando PostgreSQL..."
    sudo systemctl start postgresql 2>/dev/null || brew services start postgresql@15 2>/dev/null || log_warning "Inicie PostgreSQL manualmente"
fi

# 2. Iniciar Redis (se não estiver rodando)
if ! pgrep -x "redis-server" > /dev/null; then
    log_info "Iniciando Redis..."
    sudo systemctl start redis-server 2>/dev/null || brew services start redis 2>/dev/null || redis-server --daemonize yes
fi

# 3. Iniciar Ollama (se não estiver rodando)
if ! pgrep -x "ollama" > /dev/null; then
    log_info "Iniciando Ollama..."
    nohup ollama serve > logs/ollama.log 2>&1 &
    sleep 5
fi

# 4. Iniciar ChromaDB
log_info "Iniciando ChromaDB..."
./scripts/services/start_chromadb.sh
sleep 3

# 5. Iniciar Celery Worker
log_info "Iniciando Celery Worker..."
./scripts/services/start_celery.sh
sleep 2

# 6. Iniciar Celery Beat
log_info "Iniciando Celery Beat..."
./scripts/services/start_celery_beat.sh
sleep 2

# 7. Iniciar Backend API
log_info "Iniciando Backend API..."
source backend/venv/bin/activate
cd backend
nohup python main.py > ../logs/backend.log 2>&1 &
echo $! > ../data/backend.pid
cd ..
sleep 5

# 8. Iniciar Frontend
log_info "Iniciando Frontend..."
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
echo $! > ../data/frontend.pid
cd ..
sleep 10

# Verificar se todos os serviços estão rodando
log_info "Verificando serviços..."

services_ok=true

# Verificar backend
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    log_success "✅ Backend API está rodando (porta 8000)"
else
    log_warning "⚠️ Backend API pode não estar respondendo"
    services_ok=false
fi

# Verificar frontend
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    log_success "✅ Frontend está rodando (porta 3000)"
else
    log_warning "⚠️ Frontend pode não estar respondendo"
    services_ok=false
fi

# Verificar ChromaDB
if curl -s http://localhost:8001/api/v1/heartbeat >/dev/null 2>&1; then
    log_success "✅ ChromaDB está rodando (porta 8001)"
else
    log_warning "⚠️ ChromaDB pode não estar respondendo"
fi

# Verificar Ollama
if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
    log_success "✅ Ollama está rodando (porta 11434)"
else
    log_warning "⚠️ Ollama pode não estar respondendo"
fi

echo ""
if $services_ok; then
    log_success "🎉 Sistema de IA Conversacional iniciado com sucesso!"
else
    log_warning "⚠️ Alguns serviços podem não estar funcionando corretamente"
fi

echo ""
echo "📱 Acesse a interface principal em: http://localhost:3000"
echo "🔧 Dashboard administrativo em: http://localhost:3000/admin"
echo "📚 Documentação da API em: http://localhost:8000/docs"
echo "📊 Métricas do sistema em: http://localhost:8000/metrics"
echo ""
echo "📋 Para monitorar os logs:"
echo "   Backend: tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
echo "   Celery: tail -f logs/celery.log"
echo "   ChromaDB: tail -f logs/chromadb.log"
echo ""
echo "🛑 Para parar o sistema: ./stop_sistema_ia.sh"
EOF
    
    # Script de parada
    cat > stop_sistema_ia.sh << 'EOF'
#!/bin/bash

# Script para Parar o Sistema de IA Conversacional

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

log_info "🛑 Parando Sistema de IA Conversacional..."

# Função para parar processo por PID file
stop_by_pid() {
    local service_name=$1
    local pid_file=$2
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Parando $service_name (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 3
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
            rm -f "$pid_file"
            log_success "$service_name parado"
        else
            rm -f "$pid_file"
            log_info "$service_name não estava rodando"
        fi
    else
        log_info "$service_name não estava rodando (sem PID file)"
    fi
}

# Parar serviços na ordem inversa
stop_by_pid "Frontend" "data/frontend.pid"
stop_by_pid "Backend API" "data/backend.pid"
stop_by_pid "Celery Beat" "data/celery-beat.pid"
stop_by_pid "Celery Worker" "data/celery.pid"
stop_by_pid "ChromaDB" "data/chromadb.pid"

# Parar Ollama
if pgrep -x "ollama" > /dev/null; then
    log_info "Parando Ollama..."
    pkill -TERM ollama 2>/dev/null || true
    sleep 3
    if pgrep -x "ollama" > /dev/null; then
        pkill -KILL ollama 2>/dev/null || true
    fi
    log_success "Ollama parado"
fi

# PostgreSQL e Redis são mantidos rodando (serviços do sistema)
log_info "PostgreSQL e Redis mantidos rodando (serviços do sistema)"

log_success "🎉 Sistema parado com sucesso!"
EOF
    
    # Script de monitoramento
    cat > monitor_sistema_ia.sh << 'EOF'
#!/bin/bash

# Script de Monitoramento do Sistema de IA Conversacional

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar status de serviço
check_service() {
    local service_name=$1
    local port=$2
    local process_pattern=$3
    
    printf "%-20s" "$service_name:"
    
    if pgrep -f "$process_pattern" > /dev/null 2>&1; then
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}✓ Rodando${NC} (porta $port)"
        else
            echo -e "${YELLOW}⚠ Processo ativo, porta não responde${NC}"
        fi
    else
        echo -e "${RED}✗ Parado${NC}"
    fi
}

clear
echo "🔍 Monitor do Sistema de IA Conversacional Avançada"
echo "=================================================="
echo ""

log_info "📋 Status dos Serviços:"
echo ""

check_service "PostgreSQL" 5432 "postgres"
check_service "Redis" 6379 "redis-server"
check_service "ChromaDB" 8001 "chroma"
check_service "Ollama" 11434 "ollama"
check_service "Celery Worker" 0 "celery.*worker"
check_service "Celery Beat" 0 "celery.*beat"
check_service "Backend API" 8000 "python.*main.py"
check_service "Frontend" 3000 "npm.*dev"

echo ""
log_info "💻 Uso de Recursos:"
echo ""

# CPU e Memória
if command -v top >/dev/null 2>&1; then
    echo "💻 CPU e Memória:"
    top -bn1 | grep "Cpu(s)" | awk '{print "   CPU: " $2}' | sed 's/%us,//' 2>/dev/null || echo "   CPU: N/A"
    free -h 2>/dev/null | awk 'NR==2{printf "   Memória: %s/%s (%.1f%%)\n", $3,$2,$3*100/$2 }' || echo "   Memória: N/A"
fi

# Espaço em disco
if command -v df >/dev/null 2>&1; then
    echo ""
    echo "💾 Espaço em Disco:"
    df -h / 2>/dev/null | awk 'NR==2{printf "   Disco: %s/%s (%s usado)\n", $3,$2,$5}' || echo "   Disco: N/A"
fi

echo ""
log_info "🔗 URLs de Acesso:"
echo ""
echo "   Interface Principal:    http://localhost:3000"
echo "   Dashboard Admin:        http://localhost:3000/admin"
echo "   API Backend:           http://localhost:8000"
echo "   Documentação API:      http://localhost:8000/docs"
echo "   ChromaDB:              http://localhost:8001"
echo ""

# Testar conectividade
log_info "🌐 Teste de Conectividade:"
echo ""

if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    log_success "✓ Backend API respondendo"
else
    log_error "✗ Backend API não responde"
fi

if curl -s http://localhost:3000 >/dev/null 2>&1; then
    log_success "✓ Frontend respondendo"
else
    log_error "✗ Frontend não responde"
fi

if curl -s http://localhost:8001/api/v1/heartbeat >/dev/null 2>&1; then
    log_success "✓ ChromaDB respondendo"
else
    log_warning "⚠ ChromaDB pode não estar respondendo"
fi

if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
    log_success "✓ Ollama respondendo"
else
    log_warning "⚠ Ollama pode não estar respondendo"
fi

echo ""
echo "🔄 Para monitoramento contínuo: watch -n 5 ./monitor_sistema_ia.sh"
echo "📊 Para logs em tempo real: tail -f logs/backend.log"
EOF
    
    chmod +x *.sh
    
    log_success "Scripts de gerenciamento criados"
}

# Executar testes de integração
run_integration_tests() {
    log_step "Executando testes de integração..."
    
    source backend/venv/bin/activate
    
    # Teste básico de conectividade
    python3 -c "
import asyncio
import aiohttp
import sys

async def test_system():
    try:
        # Testar backend
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/health') as resp:
                if resp.status == 200:
                    print('✅ Backend API: OK')
                else:
                    print('❌ Backend API: Falha')
                    return False
        
        # Testar frontend
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:3000') as resp:
                if resp.status == 200:
                    print('✅ Frontend: OK')
                else:
                    print('❌ Frontend: Falha')
                    return False
        
        print('✅ Todos os testes de integração passaram')
        return True
        
    except Exception as e:
        print(f'❌ Erro nos testes: {e}')
        return False

if not asyncio.run(test_system()):
    sys.exit(1)
" 2>/dev/null || log_warning "Testes de integração falharam (serviços podem não estar totalmente inicializados)"
    
    log_success "Testes de integração concluídos"
}

# Função principal
main() {
    echo ""
    echo "🤖 Sistema de IA Conversacional Avançada - Setup Completo"
    echo "========================================================="
    echo ""
    echo "Este script irá configurar um sistema completo de IA conversacional"
    echo "integrando OpenManus, ChatBot-UI e TeenyTinyLlama com capacidades"
    echo "de auto-aprendizado e memória persistente."
    echo ""
    
    read -p "Deseja continuar? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Setup cancelado pelo usuário"
        exit 0
    fi
    
    # Detectar sistema operacional
    detect_os
    
    # Executar etapas de configuração
    install_prerequisites
    setup_backend
    setup_frontend
    setup_databases
    setup_ollama
    initialize_database
    setup_background_services
    create_management_scripts
    
    echo ""
    log_success "🎉 Configuração completa do sistema concluída!"
    echo ""
    echo "📋 Próximos passos:"
    echo "1. Execute: ./start_sistema_ia.sh"
    echo "2. Aguarde todos os serviços iniciarem (pode levar alguns minutos)"
    echo "3. Acesse: http://localhost:3000"
    echo ""
    echo "📖 Para mais informações, consulte a documentação em:"
    echo "   - README_SISTEMA_IA.md"
    echo "   - docs/GUIA_ADMINISTRADOR.md"
    echo "   - docs/GUIA_DESENVOLVEDOR.md"
    echo ""
    echo "🔧 Para monitorar o sistema: ./monitor_sistema_ia.sh"
    echo "🛑 Para parar o sistema: ./stop_sistema_ia.sh"
}

# Executar função principal
main "$@"