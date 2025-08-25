#!/bin/bash

# Script de Configuração do OpenManus
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

# Verificar se OpenManus já está configurado
if [[ -d "backend" ]]; then
    log_success "OpenManus backend já está configurado"
    exit 0
fi

log_info "=== Configuração do Backend OpenManus ==="

# Criar estrutura de diretórios
log_info "Criando estrutura de diretórios do backend..."
mkdir -p backend/{api,agents,database,services,utils,models}
mkdir -p backend/api/{routes,middleware}
mkdir -p backend/database/{migrations,schemas}
mkdir -p backend/agents/{conversation,learning,knowledge}
mkdir -p config/backend

log_success "Estrutura de diretórios criada"

# Verificar se Python está disponível
PYTHON_CMD=""
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_CMD="python3.12"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ "$PYTHON_VERSION" == "3.12" ]]; then
        PYTHON_CMD="python3"
    fi
fi

if [[ -z "$PYTHON_CMD" ]]; then
    log_error "Python 3.12 não encontrado. Execute install_prerequisites.sh primeiro"
    exit 1
fi

# Criar ambiente virtual
log_info "Criando ambiente virtual Python..."
$PYTHON_CMD -m venv backend/venv
source backend/venv/bin/activate

# Instalar dependências do backend
log_info "Instalando dependências do backend..."
pip install --upgrade pip

# Criar requirements.txt para o backend estendido
cat > backend/requirements.txt << 'EOF'
# Dependências base do OpenManus
pydantic~=2.10.6
openai~=1.66.3
tenacity~=9.0.0
loguru~=0.7.3
fastapi~=0.115.11
uvicorn~=0.34.0
tiktoken~=0.9.0

# Dependências para IA conversacional avançada
sqlalchemy~=2.0.25
asyncpg~=0.29.0
alembic~=1.13.1
redis~=5.0.1
celery~=5.3.4
chromadb~=0.4.22
sentence-transformers~=2.2.2
numpy~=1.26.3
pandas~=2.1.4
scikit-learn~=1.3.2

# Dependências para APIs e autenticação
python-jose[cryptography]~=3.3.0
passlib[bcrypt]~=1.7.4
python-multipart~=0.0.6
aiofiles~=24.1.0

# Dependências para monitoramento
prometheus-client~=0.19.0
psutil~=5.9.6

# Dependências para processamento de texto
beautifulsoup4~=4.13.3
markdownify~=0.11.6
EOF

pip install -r backend/requirements.txt

log_success "Dependências do backend instaladas"

# Configurar variáveis de ambiente
log_info "Configurando variáveis de ambiente..."
cat > config/backend/.env << 'EOF'
# Configuração do Sistema de IA Conversacional

# Banco de Dados PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/openmanus_ai
SQLALCHEMY_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/openmanus_ai

# Redis
REDIS_URL=redis://localhost:6379/0

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8001

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=tinyllama

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=sua_chave_secreta_super_segura_aqui_mude_em_producao

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Configurações de Aprendizado
ENABLE_AUTO_LEARNING=true
FEEDBACK_THRESHOLD=3
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Configurações de Monitoramento
ENABLE_METRICS=true
METRICS_PORT=9090
EOF

log_success "Arquivo de configuração criado em config/backend/.env"

log_info "✅ Configuração do OpenManus concluída!"
log_info "Próximo passo: Execute ./scripts/setup_chatbot_ui.sh"