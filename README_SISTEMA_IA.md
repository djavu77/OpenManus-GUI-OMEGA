# Sistema de IA Conversacional Avançada - OpenManus

## Visão Geral

Este sistema integra OpenManus, ChatBot-UI e TeenyTinyLlama para criar uma plataforma de IA conversacional com capacidades de auto-aprendizado, memória persistente e evolução contínua.

## Arquitetura do Sistema

### Backend
- **OpenManus**: Framework de agentes IA (já configurado)
- **FastAPI**: APIs REST customizadas
- **PostgreSQL**: Dados estruturados
- **ChromaDB**: Embeddings e busca semântica
- **Redis**: Cache e sessões
- **Ollama + TeenyTinyLlama**: Processamento de linguagem
- **Celery**: Tarefas assíncronas

### Frontend
- **ChatBot-UI**: Interface customizada
- **Dashboard Admin**: Métricas e monitoramento
- **Sistema de Feedback**: Avaliação em tempo real

## Instalação Rápida

```bash
# 1. Instalar pré-requisitos
chmod +x scripts/install_prerequisites.sh
./scripts/install_prerequisites.sh

# 2. Configurar OpenManus (já configurado)
chmod +x scripts/setup_openmanus.sh
./scripts/setup_openmanus.sh

# 3. Configurar ChatBot-UI
chmod +x scripts/setup_chatbot_ui.sh
./scripts/setup_chatbot_ui.sh

# 4. Iniciar sistema completo
chmod +x scripts/start_system.sh
./scripts/start_system.sh
```

## Funcionalidades Principais

- ✅ Auto-aprendizado baseado em feedback
- ✅ Memória persistente de longo prazo
- ✅ Sistema multi-agente colaborativo
- ✅ Busca semântica avançada
- ✅ Dashboard de métricas em tempo real
- ✅ API REST completa
- ✅ Interface moderna e responsiva

## Acesso ao Sistema

- **Interface Principal**: http://localhost:3000
- **Dashboard Admin**: http://localhost:3000/admin
- **API Docs**: http://localhost:8000/docs
- **Métricas**: http://localhost:3000/metrics

## Estrutura do Projeto

```
sistema-ia-conversacional/
├── backend/
│   ├── api/                 # APIs FastAPI customizadas
│   ├── agents/              # Agentes especializados
│   ├── database/            # Schemas e migrações
│   ├── services/            # Serviços de negócio
│   └── utils/               # Utilitários
├── frontend/
│   ├── chatbot-ui/          # Interface principal
│   ├── admin-dashboard/     # Dashboard administrativo
│   └── components/          # Componentes customizados
├── scripts/                 # Scripts de automação
├── config/                  # Configurações
└── docs/                    # Documentação
```