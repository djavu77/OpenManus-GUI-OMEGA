#!/bin/bash

# Script de Monitoramento do Sistema
# Sistema de IA Conversacional Avançada

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

# Função para verificar status de serviço
check_service_status() {
    local service_name=$1
    local port=$2
    local process_pattern=$3
    
    printf "%-20s" "$service_name:"
    
    # Verificar se processo está rodando
    if pgrep -f "$process_pattern" > /dev/null 2>&1; then
        # Verificar se porta está aberta
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}✓ Rodando${NC} (porta $port)"
        else
            echo -e "${YELLOW}⚠ Processo ativo, porta não responde${NC}"
        fi
    else
        echo -e "${RED}✗ Parado${NC}"
    fi
}

# Função para mostrar uso de recursos
show_resource_usage() {
    echo ""
    log_info "📊 Uso de Recursos do Sistema:"
    echo ""
    
    # CPU e Memória
    echo "💻 CPU e Memória:"
    top -bn1 | grep "Cpu(s)" | awk '{print "   CPU: " $2}' | sed 's/%us,//'
    free -h | awk 'NR==2{printf "   Memória: %s/%s (%.1f%%)\n", $3,$2,$3*100/$2 }'
    
    echo ""
    
    # Espaço em disco
    echo "💾 Espaço em Disco:"
    df -h / | awk 'NR==2{printf "   Disco: %s/%s (%s usado)\n", $3,$2,$5}'
    
    echo ""
    
    # Processos do sistema
    echo "🔄 Processos Principais:"
    ps aux | grep -E "(ollama|uvicorn|next|celery|chromadb)" | grep -v grep | awk '{printf "   %-15s %s%%\n", $11, $3}' | head -10
}

# Função para mostrar logs recentes
show_recent_logs() {
    echo ""
    log_info "📝 Logs Recentes (últimas 5 linhas):"
    echo ""
    
    local log_files=("backend.log" "frontend.log" "celery.log" "chromadb.log" "ollama.log")
    
    for log_file in "${log_files[@]}"; do
        if [[ -f "logs/$log_file" ]]; then
            echo "📄 $log_file:"
            tail -n 3 "logs/$log_file" | sed 's/^/   /'
            echo ""
        fi
    done
}

# Função para testar conectividade da API
test_api_connectivity() {
    echo ""
    log_info "🔗 Testando Conectividade da API:"
    echo ""
    
    # Testar endpoint de saúde
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        log_success "✓ Endpoint /health respondendo"
    else
        log_error "✗ Endpoint /health não responde"
    fi
    
    # Testar endpoint de modelos
    if curl -s http://localhost:8000/v1/models >/dev/null 2>&1; then
        log_success "✓ Endpoint /v1/models respondendo"
    else
        log_error "✗ Endpoint /v1/models não responde"
    fi
    
    # Testar frontend
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        log_success "✓ Frontend respondendo"
    else
        log_error "✗ Frontend não responde"
    fi
}

# Função para mostrar informações de conexão
show_connection_info() {
    echo ""
    log_info "🌐 Informações de Conexão:"
    echo ""
    echo "   Interface Principal:    http://localhost:3000"
    echo "   Dashboard Admin:        http://localhost:3000/admin"
    echo "   API Backend:           http://localhost:8000"
    echo "   Documentação API:      http://localhost:8000/docs"
    echo "   ChromaDB:              http://localhost:8001"
    echo "   Métricas Prometheus:   http://localhost:9090"
    echo ""
}

# Função principal
main() {
    clear
    echo "🔍 Monitor do Sistema de IA Conversacional"
    echo "=========================================="
    echo ""
    
    log_info "📋 Status dos Serviços:"
    echo ""
    
    # Verificar status de cada serviço
    check_service_status "PostgreSQL" 5432 "postgres"
    check_service_status "Redis" 6379 "redis-server"
    check_service_status "ChromaDB" 8001 "chromadb"
    check_service_status "Ollama" 11434 "ollama"
    check_service_status "Celery Worker" 0 "celery.*worker"
    check_service_status "Backend API" 8000 "uvicorn.*backend.api.main"
    check_service_status "Frontend" 3000 "next.*dev"
    
    # Mostrar uso de recursos
    show_resource_usage
    
    # Testar conectividade
    test_api_connectivity
    
    # Mostrar logs recentes
    show_recent_logs
    
    # Mostrar informações de conexão
    show_connection_info
    
    echo "🔄 Para monitoramento contínuo: watch -n 5 ./scripts/monitor_system.sh"
    echo "📊 Para logs em tempo real: tail -f logs/backend.log"
}

# Verificar se nc (netcat) está disponível
if ! command -v nc >/dev/null 2>&1; then
    log_warning "netcat (nc) não encontrado. Instalando..."
    case "$OSTYPE" in
        "linux-gnu"*)
            sudo apt-get update && sudo apt-get install -y netcat-openbsd
            ;;
        "darwin"*)
            brew install netcat
            ;;
    esac
fi

# Executar função principal
main "$@"