#!/bin/bash

# Script de Inicialização do Sistema Completo
# Sistema de IA Conversacional Avançada

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Função para verificar se serviço está rodando
check_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    log_info "Verificando $service_name na porta $port..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if nc -z localhost $port 2>/dev/null; then
            log_success "$service_name está rodando na porta $port"
            return 0
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "$service_name não está respondendo na porta $port após $max_attempts tentativas"
            return 1
        fi
        
        sleep 2
        ((attempt++))
    done
}

# Função para iniciar PostgreSQL
start_postgresql() {
    log_info "Iniciando PostgreSQL..."
    
    if pgrep -x "postgres" > /dev/null; then
        log_success "PostgreSQL já está rodando"
    else
        case "$OSTYPE" in
            "linux-gnu"*)
                sudo systemctl start postgresql
                ;;
            "darwin"*)
                brew services start postgresql@15
                ;;
            *)
                log_warning "Sistema não reconhecido. Inicie PostgreSQL manualmente"
                ;;
        esac
    fi
    
    # Criar banco de dados se não existir
    log_info "Configurando banco de dados..."
    createdb openmanus_ai 2>/dev/null || log_info "Banco de dados já existe"
    
    check_service "PostgreSQL" 5432
}

# Função para iniciar Redis
start_redis() {
    log_info "Iniciando Redis..."
    
    if pgrep -x "redis-server" > /dev/null; then
        log_success "Redis já está rodando"
    else
        case "$OSTYPE" in
            "linux-gnu"*)
                sudo systemctl start redis-server
                ;;
            "darwin"*)
                brew services start redis
                ;;
            *)
                redis-server --daemonize yes
                ;;
        esac
    fi
    
    check_service "Redis" 6379
}

# Função para iniciar ChromaDB
start_chromadb() {
    log_info "Iniciando ChromaDB..."
    
    if pgrep -f "chromadb" > /dev/null; then
        log_success "ChromaDB já está rodando"
    else
        # Ativar ambiente virtual do backend
        source backend/venv/bin/activate
        
        # Iniciar ChromaDB em background
        nohup chroma run --host localhost --port 8001 > logs/chromadb.log 2>&1 &
        
        sleep 5
    fi
    
    check_service "ChromaDB" 8001
}

# Função para iniciar Ollama
start_ollama() {
    log_info "Iniciando Ollama..."
    
    if pgrep -x "ollama" > /dev/null; then
        log_success "Ollama já está rodando"
    else
        nohup ollama serve > logs/ollama.log 2>&1 &
        sleep 5
    fi
    
    check_service "Ollama" 11434
    
    # Verificar se modelo está disponível
    log_info "Verificando modelo TeenyTinyLlama..."
    if ollama list | grep -q "tinyllama"; then
        log_success "Modelo TeenyTinyLlama está disponível"
    else
        log_info "Baixando modelo TeenyTinyLlama..."
        ollama pull tinyllama
    fi
}

# Função para iniciar Celery
start_celery() {
    log_info "Iniciando Celery Worker..."
    
    if pgrep -f "celery.*worker" > /dev/null; then
        log_success "Celery Worker já está rodando"
    else
        source backend/venv/bin/activate
        cd backend
        nohup celery -A services.celery_app worker --loglevel=info > ../logs/celery.log 2>&1 &
        cd ..
        sleep 3
    fi
    
    log_success "Celery Worker iniciado"
}

# Função para iniciar Backend API
start_backend() {
    log_info "Iniciando Backend API (FastAPI)..."
    
    if pgrep -f "uvicorn.*backend.api.main" > /dev/null; then
        log_success "Backend API já está rodando"
    else
        source backend/venv/bin/activate
        cd backend
        nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
        cd ..
        sleep 5
    fi
    
    check_service "Backend API" 8000
}

# Função para iniciar Frontend
start_frontend() {
    log_info "Iniciando Frontend (Next.js)..."
    
    if pgrep -f "next.*dev" > /dev/null; then
        log_success "Frontend já está rodando"
    else
        cd frontend
        nohup npm run dev > ../logs/frontend.log 2>&1 &
        cd ..
        sleep 10
    fi
    
    check_service "Frontend" 3000
}

# Função principal
main() {
    log_info "🚀 Iniciando Sistema de IA Conversacional Avançada..."
    
    # Criar diretório de logs
    mkdir -p logs
    
    # Carregar variáveis de ambiente
    if [[ -f "config/backend/.env" ]]; then
        source config/backend/.env
        log_info "Variáveis de ambiente carregadas"
    else
        log_warning "Arquivo .env não encontrado. Usando configurações padrão"
    fi
    
    # Iniciar serviços na ordem correta
    start_postgresql
    start_redis
    start_chromadb
    start_ollama
    start_celery
    start_backend
    start_frontend
    
    # Verificação final
    log_info "Realizando verificação final do sistema..."
    
    sleep 5
    
    # Testar conectividade da API
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        log_success "✅ Backend API está respondendo"
    else
        log_warning "⚠️ Backend API pode não estar totalmente inicializado"
    fi
    
    # Testar frontend
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        log_success "✅ Frontend está respondendo"
    else
        log_warning "⚠️ Frontend pode não estar totalmente inicializado"
    fi
    
    echo ""
    log_success "🎉 Sistema de IA Conversacional iniciado com sucesso!"
    echo ""
    echo "📱 Acesse a interface principal em: http://localhost:3000"
    echo "🔧 Dashboard administrativo em: http://localhost:3000/admin"
    echo "📚 Documentação da API em: http://localhost:8000/docs"
    echo "📊 Métricas do sistema em: http://localhost:3000/metrics"
    echo ""
    echo "📋 Para monitorar os logs:"
    echo "   Backend: tail -f logs/backend.log"
    echo "   Frontend: tail -f logs/frontend.log"
    echo "   Celery: tail -f logs/celery.log"
    echo ""
    echo "🛑 Para parar o sistema: ./scripts/stop_system.sh"
}

# Executar função principal
main "$@"