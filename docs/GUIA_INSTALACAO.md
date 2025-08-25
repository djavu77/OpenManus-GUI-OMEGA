# Guia de Instalação - Sistema de IA Conversacional Avançada

## Visão Geral

Este guia fornece instruções detalhadas para instalar e configurar o Sistema de IA Conversacional Avançada, que integra OpenManus, ChatBot-UI e TeenyTinyLlama para criar uma plataforma robusta com capacidades de auto-aprendizado e memória persistente.

## Pré-requisitos

### Requisitos de Sistema

- **Sistema Operacional**: Linux (Ubuntu 20.04+, Debian 11+) ou macOS 12+
- **RAM**: Mínimo 8GB, recomendado 16GB+
- **Armazenamento**: Mínimo 20GB livres
- **CPU**: 4 cores recomendado
- **Rede**: Conexão com internet para download de dependências

### Software Necessário

- Python 3.12+
- Node.js 18+
- PostgreSQL 13+
- Redis 6+
- Docker (opcional, para ChromaDB)
- Git

## Instalação Rápida

### Opção 1: Script Automatizado (Recomendado)

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/sistema-ia-conversacional.git
cd sistema-ia-conversacional

# 2. Execute o script de configuração completa
chmod +x scripts/setup_complete_system.sh
./scripts/setup_complete_system.sh

# 3. Inicie o sistema
./start_sistema_ia.sh

# 4. Acesse a interface
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Opção 2: Instalação Manual

#### Passo 1: Instalar Pré-requisitos

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-pip
sudo apt install -y nodejs npm postgresql postgresql-contrib redis-server
sudo apt install -y git curl wget build-essential

# macOS (com Homebrew)
brew install python@3.12 node@20 postgresql@15 redis git
brew services start postgresql@15
brew services start redis
```

#### Passo 2: Instalar Ollama e TeenyTinyLlama

```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar Ollama
ollama serve &

# Baixar modelo TeenyTinyLlama
ollama pull tinyllama

# Testar modelo
ollama run tinyllama "Olá, você está funcionando?"
```

#### Passo 3: Configurar Backend

```bash
# Criar ambiente virtual
python3.12 -m venv backend/venv
source backend/venv/bin/activate

# Instalar dependências do OpenManus
pip install -r requirements.txt

# Instalar dependências adicionais
pip install sqlalchemy[asyncio] asyncpg redis celery chromadb
pip install sentence-transformers scikit-learn pandas
pip install python-jose[cryptography] passlib[bcrypt]
pip install prometheus-client psutil

# Configurar banco de dados
sudo -u postgres createdb sistema_ia_conversacional
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

# Executar migrações
python backend/services/database_service.py
```

#### Passo 4: Configurar Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Configurar variáveis de ambiente
cp .env.example .env.local
# Editar .env.local com suas configurações

cd ..
```

#### Passo 5: Configurar ChromaDB

```bash
# Opção 1: Via Docker (Recomendado)
docker run -d --name chromadb \
  -p 8001:8000 \
  -v ./data/chromadb:/chroma/chroma \
  chromadb/chroma:latest

# Opção 2: Via Python
source backend/venv/bin/activate
pip install chromadb
mkdir -p data/chromadb
nohup chroma run --host localhost --port 8001 --path ./data/chromadb &
```

## Configuração Detalhada

### Variáveis de Ambiente

#### Backend (.env)

```bash
# Banco de Dados
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sistema_ia_conversacional
REDIS_URL=redis://localhost:6379/0

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8001

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=tinyllama

# API
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=sua_chave_secreta_aqui

# Aprendizado
ENABLE_AUTO_LEARNING=true
FEEDBACK_THRESHOLD=3
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

#### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_APP_NAME=Sistema IA Conversacional
NEXT_PUBLIC_ENABLE_FEEDBACK=true
NEXT_PUBLIC_ENABLE_METRICS=true
```

### Configuração do PostgreSQL

```sql
-- Criar banco de dados
CREATE DATABASE sistema_ia_conversacional;

-- Criar usuário (opcional)
CREATE USER sistema_ia WITH PASSWORD 'senha_segura';
GRANT ALL PRIVILEGES ON DATABASE sistema_ia_conversacional TO sistema_ia;

-- Conectar ao banco e criar extensões
\c sistema_ia_conversacional;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### Configuração do Redis

```bash
# Editar configuração do Redis (opcional)
sudo nano /etc/redis/redis.conf

# Configurações recomendadas:
# maxmemory 2gb
# maxmemory-policy allkeys-lru
# save 900 1
# save 300 10
# save 60 10000

# Reiniciar Redis
sudo systemctl restart redis-server
```

## Inicialização do Sistema

### Ordem de Inicialização

1. **PostgreSQL** - Banco de dados principal
2. **Redis** - Cache e sessões
3. **Ollama** - Servidor de modelo de linguagem
4. **ChromaDB** - Banco de dados vetorial
5. **Celery Worker** - Processamento assíncrono
6. **Backend API** - Servidor FastAPI
7. **Frontend** - Interface Next.js

### Scripts de Inicialização

```bash
# Iniciar sistema completo
./start_sistema_ia.sh

# Iniciar serviços individuais
./scripts/services/start_chromadb.sh
./scripts/services/start_celery.sh
./scripts/services/start_backend.sh
./scripts/services/start_frontend.sh

# Monitorar sistema
./monitor_sistema_ia.sh

# Parar sistema
./stop_sistema_ia.sh
```

## Verificação da Instalação

### Testes de Conectividade

```bash
# Testar PostgreSQL
psql -h localhost -U postgres -d sistema_ia_conversacional -c "SELECT version();"

# Testar Redis
redis-cli ping

# Testar Ollama
curl http://localhost:11434/api/version

# Testar ChromaDB
curl http://localhost:8001/api/v1/heartbeat

# Testar Backend API
curl http://localhost:8000/health

# Testar Frontend
curl http://localhost:3000
```

### Testes Funcionais

```bash
# Teste de chat via API
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openmanus-tinyllama",
    "messages": [{"role": "user", "content": "Olá, como você está?"}],
    "stream": false
  }'

# Teste de feedback
curl -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test-message-id",
    "rating": 5,
    "comment": "Resposta excelente!"
  }'

# Teste de métricas
curl http://localhost:8000/api/metrics
```

## Solução de Problemas

### Problemas Comuns

#### 1. Erro de Conexão com PostgreSQL

```bash
# Verificar se PostgreSQL está rodando
sudo systemctl status postgresql

# Verificar logs
sudo tail -f /var/log/postgresql/postgresql-*.log

# Reiniciar serviço
sudo systemctl restart postgresql
```

#### 2. Ollama não responde

```bash
# Verificar processo
pgrep -f ollama

# Verificar logs
tail -f logs/ollama.log

# Reiniciar Ollama
pkill ollama
ollama serve &
```

#### 3. ChromaDB falha ao iniciar

```bash
# Verificar permissões do diretório
ls -la data/chromadb

# Limpar dados corrompidos
rm -rf data/chromadb/*
./scripts/services/start_chromadb.sh
```

#### 4. Frontend não carrega

```bash
# Verificar dependências
cd frontend
npm install

# Verificar logs
tail -f logs/frontend.log

# Limpar cache
rm -rf frontend/.next
npm run build
```

### Logs e Debugging

```bash
# Logs principais
tail -f logs/backend.log      # API Backend
tail -f logs/frontend.log     # Interface
tail -f logs/celery.log       # Tarefas assíncronas
tail -f logs/chromadb.log     # Banco vetorial
tail -f logs/ollama.log       # Modelo de linguagem

# Logs do sistema
journalctl -u postgresql -f   # PostgreSQL
journalctl -u redis -f        # Redis

# Monitoramento em tempo real
watch -n 2 './monitor_sistema_ia.sh'
```

## Configuração Avançada

### Otimização de Performance

```bash
# PostgreSQL
sudo nano /etc/postgresql/*/main/postgresql.conf
# Ajustar: shared_buffers, effective_cache_size, work_mem

# Redis
sudo nano /etc/redis/redis.conf
# Ajustar: maxmemory, maxmemory-policy

# Ollama
export OLLAMA_NUM_PARALLEL=2
export OLLAMA_MAX_LOADED_MODELS=1
```

### Configuração de Produção

```bash
# Configurar proxy reverso (Nginx)
sudo apt install nginx
sudo nano /etc/nginx/sites-available/sistema-ia

# Configurar SSL/TLS
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com

# Configurar firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Backup e Recuperação

```bash
# Backup automático do PostgreSQL
crontab -e
# Adicionar: 0 2 * * * pg_dump sistema_ia_conversacional > /backup/db_$(date +\%Y\%m\%d).sql

# Backup da base de conhecimento
./scripts/backup_knowledge_base.sh

# Backup completo do sistema
./scripts/full_system_backup.sh
```

## Próximos Passos

Após a instalação bem-sucedida:

1. **Acesse a interface**: http://localhost:3000
2. **Configure usuário admin**: http://localhost:3000/admin
3. **Teste o sistema**: Faça algumas perguntas para testar
4. **Configure monitoramento**: Verifique métricas em tempo real
5. **Leia a documentação**: Consulte os guias de usuário e desenvolvedor

## Suporte

Para problemas ou dúvidas:

- **Documentação**: Consulte os arquivos em `docs/`
- **Logs**: Verifique os arquivos em `logs/`
- **Issues**: Abra uma issue no repositório GitHub
- **Monitoramento**: Use `./monitor_sistema_ia.sh` para diagnóstico

---

**Nota**: Este sistema é projetado para aprender e evoluir continuamente. Quanto mais você usar e fornecer feedback, melhor ele se tornará!