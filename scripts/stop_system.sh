#!/bin/bash

# Script para Parar o Sistema Completo
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

# Função para parar processo por nome
stop_process() {
    local process_name=$1
    local service_name=$2
    
    log_info "Parando $service_name..."
    
    local pids=$(pgrep -f "$process_name" 2>/dev/null || true)
    
    if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 3
        
        # Verificar se ainda está rodando e forçar parada
        local remaining_pids=$(pgrep -f "$process_name" 2>/dev/null || true)
        if [[ -n "$remaining_pids" ]]; then
            log_warning "Forçando parada de $service_name..."
            echo "$remaining_pids" | xargs kill -KILL 2>/dev/null || true
        fi
        
        log_success "$service_name parado"
    else
        log_info "$service_name não estava rodando"
    fi
}

# Função principal
main() {
    log_info "🛑 Parando Sistema de IA Conversacional..."
    
    # Parar serviços na ordem inversa da inicialização
    stop_process "next.*dev" "Frontend (Next.js)"
    stop_process "uvicorn.*backend.api.main" "Backend API (FastAPI)"
    stop_process "celery.*worker" "Celery Worker"
    stop_process "chromadb" "ChromaDB"
    
    # Parar Ollama
    log_info "Parando Ollama..."
    if pgrep -x "ollama" > /dev/null; then
        pkill -TERM ollama 2>/dev/null || true
        sleep 3
        if pgrep -x "ollama" > /dev/null; then
            pkill -KILL ollama 2>/dev/null || true
        fi
        log_success "Ollama parado"
    else
        log_info "Ollama não estava rodando"
    fi
    
    # Redis e PostgreSQL são mantidos rodando por serem serviços do sistema
    log_info "Redis e PostgreSQL mantidos rodando (serviços do sistema)"
    
    # Limpar arquivos temporários
    log_info "Limpando arquivos temporários..."
    rm -f logs/*.log 2>/dev/null || true
    
    log_success "🎉 Sistema parado com sucesso!"
    echo ""
    echo "Para reiniciar o sistema: ./scripts/start_system.sh"
}

# Executar função principal
main "$@"