"""
API Principal do Sistema de IA Conversacional Avançada
Integração com OpenManus e funcionalidades estendidas
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz do OpenManus ao path
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
import json
import uuid
import time
from typing import List, Optional, Dict, Any

# Importações do OpenManus
from app.agent.manus import Manus
from app.schema import AgentState, Message as AgentMessage
from app.logger import logger

# Importações locais
from backend.database.connection import get_db_session, init_database
from backend.services.feedback_service import FeedbackService
from backend.services.knowledge_service import KnowledgeService
from backend.services.metrics_service import MetricsService
from backend.models.api_models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    FeedbackRequest,
    KnowledgeRequest,
    HealthResponse
)

# Inicialização do agente global
agent_instance: Optional[Manus] = None
agent_lock = asyncio.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando Sistema de IA Conversacional...")
    
    # Inicializar banco de dados
    await init_database()
    
    # Inicializar agente OpenManus
    global agent_instance
    agent_instance = Manus()
    agent_instance.state = AgentState.IDLE
    
    logger.info("✅ Sistema inicializado com sucesso")
    
    yield
    
    # Shutdown
    logger.info("🛑 Encerrando sistema...")
    if agent_instance:
        await agent_instance.cleanup()

# Criar aplicação FastAPI
app = FastAPI(
    title="Sistema de IA Conversacional Avançada",
    description="API para sistema de IA com auto-aprendizado e memória persistente",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serviços
feedback_service = FeedbackService()
knowledge_service = KnowledgeService()
metrics_service = MetricsService()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verificação de saúde do sistema"""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        services={
            "openmanus": agent_instance is not None,
            "database": True,  # TODO: verificar conexão real
            "redis": True,     # TODO: verificar conexão real
            "chromadb": True,  # TODO: verificar conexão real
        }
    )

@app.get("/v1/models")
async def list_models():
    """Listar modelos disponíveis (compatibilidade OpenAI)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "openmanus-tinyllama",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "openmanus"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    db_session = Depends(get_db_session)
):
    """Endpoint principal para chat (compatível com OpenAI)"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agente não inicializado")
    
    async with agent_lock:
        try:
            # Resetar estado do agente
            agent_instance.memory.messages = []
            agent_instance.state = AgentState.IDLE
            agent_instance.current_step = 0
            
            # Converter mensagens para formato do OpenManus
            for msg in request.messages:
                agent_msg = AgentMessage(
                    role=msg.role,
                    content=msg.content or ""
                )
                agent_instance.memory.add_message(agent_msg)
            
            # Obter última mensagem do usuário
            last_user_message = ""
            for msg in reversed(request.messages):
                if msg.role == "user":
                    last_user_message = msg.content or ""
                    break
            
            request_id = f"chatcmpl-{uuid.uuid4().hex}"
            
            # Buscar contexto relevante da base de conhecimento
            relevant_context = await knowledge_service.search_relevant_context(
                query=last_user_message,
                limit=3
            )
            
            if relevant_context:
                context_msg = AgentMessage(
                    role="system",
                    content=f"Contexto relevante da base de conhecimento:\n{relevant_context}"
                )
                agent_instance.memory.add_message(context_msg)
            
            # Processar com streaming se solicitado
            if request.stream:
                return StreamingResponse(
                    stream_chat_response(agent_instance, last_user_message, request_id, background_tasks, db_session),
                    media_type="text/event-stream"
                )
            else:
                # Resposta não-streaming
                final_response = ""
                async for update in agent_instance.run(request=last_user_message):
                    final_response = update
                
                # Salvar conversa em background
                background_tasks.add_task(
                    save_conversation_to_db,
                    db_session,
                    request.messages,
                    final_response
                )
                
                return ChatCompletionResponse(
                    id=request_id,
                    model=request.model,
                    choices=[{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": final_response
                        },
                        "finish_reason": "stop"
                    }]
                )
                
        except Exception as e:
            logger.error(f"Erro no chat completion: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

async def stream_chat_response(agent, user_message, request_id, background_tasks, db_session):
    """Gerar resposta streaming"""
    try:
        previous_content = ""
        
        async for update in agent.run(request=user_message):
            delta_content = update[len(previous_content):]
            previous_content = update
            
            if delta_content:
                chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "openmanus-tinyllama",
                    "choices": [{
                        "index": 0,
                        "delta": {"content": delta_content},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.01)
        
        # Chunk final
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "openmanus-tinyllama",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
        # Salvar conversa em background
        background_tasks.add_task(
            save_conversation_to_db,
            db_session,
            [{"role": "user", "content": user_message}],
            previous_content
        )
        
    except Exception as e:
        logger.error(f"Erro no streaming: {e}", exc_info=True)
        error_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "openmanus-tinyllama",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "error"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"

@app.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db_session = Depends(get_db_session)
):
    """Receber feedback do usuário"""
    try:
        # Salvar feedback no banco
        feedback_id = await feedback_service.save_feedback(
            db_session,
            feedback.message_id,
            feedback.user_id,
            feedback.rating,
            feedback.comment
        )
        
        # Processar feedback em background para aprendizado
        background_tasks.add_task(
            process_feedback_for_learning,
            feedback_id,
            feedback.rating,
            feedback.comment
        )
        
        return {"status": "success", "message": "Feedback recebido", "feedback_id": feedback_id}
        
    except Exception as e:
        logger.error(f"Erro ao processar feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/knowledge_base/{knowledge_id}")
async def get_knowledge_item(
    knowledge_id: str,
    db_session = Depends(get_db_session)
):
    """Recuperar item da base de conhecimento"""
    try:
        item = await knowledge_service.get_knowledge_item(db_session, knowledge_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item não encontrado")
        return item
    except Exception as e:
        logger.error(f"Erro ao buscar conhecimento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/knowledge_base")
async def add_knowledge_item(
    knowledge: KnowledgeRequest,
    background_tasks: BackgroundTasks,
    db_session = Depends(get_db_session)
):
    """Adicionar item à base de conhecimento"""
    try:
        knowledge_id = await knowledge_service.add_knowledge_item(
            db_session,
            knowledge.title,
            knowledge.content,
            knowledge.category,
            knowledge.tags,
            knowledge.source
        )
        
        # Gerar embeddings em background
        background_tasks.add_task(
            generate_embeddings_for_knowledge,
            knowledge_id,
            knowledge.content
        )
        
        return {"status": "success", "knowledge_id": knowledge_id}
        
    except Exception as e:
        logger.error(f"Erro ao adicionar conhecimento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_system_metrics(db_session = Depends(get_db_session)):
    """Obter métricas do sistema"""
    try:
        metrics = await metrics_service.get_system_metrics(db_session)
        return metrics
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Funções auxiliares para tarefas em background
async def save_conversation_to_db(db_session, messages, response):
    """Salvar conversa no banco de dados"""
    try:
        # TODO: Implementar salvamento da conversa
        logger.info("Conversa salva no banco de dados")
    except Exception as e:
        logger.error(f"Erro ao salvar conversa: {e}", exc_info=True)

async def process_feedback_for_learning(feedback_id, rating, comment):
    """Processar feedback para aprendizado (tarefa Celery)"""
    try:
        # TODO: Implementar processamento de feedback
        logger.info(f"Processando feedback {feedback_id} para aprendizado")
    except Exception as e:
        logger.error(f"Erro ao processar feedback: {e}", exc_info=True)

async def generate_embeddings_for_knowledge(knowledge_id, content):
    """Gerar embeddings para item de conhecimento (tarefa Celery)"""
    try:
        # TODO: Implementar geração de embeddings
        logger.info(f"Gerando embeddings para conhecimento {knowledge_id}")
    except Exception as e:
        logger.error(f"Erro ao gerar embeddings: {e}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)