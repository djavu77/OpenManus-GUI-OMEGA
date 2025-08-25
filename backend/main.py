"""
Sistema de IA Conversacional Avançada - Servidor Principal
Integração completa com OpenManus, PostgreSQL, ChromaDB, Redis e Celery
"""

import os
import sys
import asyncio
import json
import uuid
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, AsyncGenerator

# Adicionar diretório raiz ao path para importar módulos do OpenManus
current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn

# Importações do OpenManus
from app.agent.manus import Manus
from app.schema import AgentState, Message as AgentMessage
from app.logger import logger

# Importações dos serviços locais
from services.database_service import DatabaseService, get_db_session
from services.ai_service import AIService
from services.feedback_service import FeedbackService
from services.knowledge_service import KnowledgeService
from services.metrics_service import MetricsService
from services.learning_service import LearningService
from models.api_models import *

# Configurações globais
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/sistema_ia")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8001"))

# Instâncias globais dos serviços
ai_service: Optional[AIService] = None
feedback_service: Optional[FeedbackService] = None
knowledge_service: Optional[KnowledgeService] = None
metrics_service: Optional[MetricsService] = None
learning_service: Optional[LearningService] = None
database_service: Optional[DatabaseService] = None

# Lock para operações críticas
system_lock = asyncio.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação"""
    global ai_service, feedback_service, knowledge_service, metrics_service, learning_service, database_service
    
    logger.info("🚀 Iniciando Sistema de IA Conversacional Avançada...")
    
    try:
        # Inicializar serviços
        database_service = DatabaseService(DATABASE_URL)
        await database_service.initialize()
        
        ai_service = AIService()
        await ai_service.initialize()
        
        feedback_service = FeedbackService(database_service)
        knowledge_service = KnowledgeService(database_service, CHROMADB_HOST, CHROMADB_PORT)
        await knowledge_service.initialize()
        
        metrics_service = MetricsService(database_service, REDIS_URL)
        await metrics_service.initialize()
        
        learning_service = LearningService(
            database_service, 
            knowledge_service, 
            metrics_service,
            ai_service
        )
        
        logger.info("✅ Todos os serviços inicializados com sucesso")
        
        # Registrar métricas de inicialização
        await metrics_service.record_system_metric("system_startup", 1.0, {"status": "success"})
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização do sistema: {e}", exc_info=True)
        raise
    
    yield
    
    # Cleanup
    logger.info("🛑 Encerrando sistema...")
    try:
        if ai_service:
            await ai_service.cleanup()
        if knowledge_service:
            await knowledge_service.cleanup()
        if metrics_service:
            await metrics_service.cleanup()
        if database_service:
            await database_service.cleanup()
        logger.info("✅ Cleanup concluído")
    except Exception as e:
        logger.error(f"❌ Erro durante cleanup: {e}", exc_info=True)

# Criar aplicação FastAPI
app = FastAPI(
    title="Sistema de IA Conversacional Avançada",
    description="Plataforma de IA com auto-aprendizado, memória persistente e evolução contínua",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para métricas de requisições
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Registrar métricas da requisição
    if metrics_service:
        await metrics_service.record_request_metric(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            response_time=process_time
        )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Endpoints principais

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verificação de saúde do sistema"""
    services_status = {}
    
    try:
        # Verificar cada serviço
        services_status["database"] = await database_service.health_check() if database_service else False
        services_status["ai_service"] = await ai_service.health_check() if ai_service else False
        services_status["knowledge_base"] = await knowledge_service.health_check() if knowledge_service else False
        services_status["metrics"] = await metrics_service.health_check() if metrics_service else False
        
        overall_status = "healthy" if all(services_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=time.time(),
            services=services_status,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=time.time(),
            services=services_status,
            version="1.0.0"
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
                "owned_by": "sistema-ia-conversacional",
                "permission": [],
                "root": "openmanus-tinyllama",
                "parent": None
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session)
):
    """Endpoint principal para chat com IA (compatível com OpenAI)"""
    if not ai_service:
        raise HTTPException(status_code=503, detail="Serviço de IA não disponível")
    
    try:
        request_id = f"chatcmpl-{uuid.uuid4().hex}"
        start_time = time.time()
        
        # Extrair última mensagem do usuário
        last_user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                last_user_message = msg.content or ""
                break
        
        if not last_user_message:
            raise HTTPException(status_code=400, detail="Nenhuma mensagem do usuário encontrada")
        
        # Buscar contexto relevante da base de conhecimento
        relevant_context = ""
        if knowledge_service:
            relevant_context = await knowledge_service.search_relevant_context(
                query=last_user_message,
                limit=3
            )
        
        # Processar com streaming se solicitado
        if request.stream:
            return StreamingResponse(
                stream_chat_response(
                    request, last_user_message, relevant_context, 
                    request_id, start_time, background_tasks, db_session
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # Resposta não-streaming
            response_content = await ai_service.generate_response(
                messages=request.messages,
                context=relevant_context,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            response_time = time.time() - start_time
            
            # Salvar conversa em background
            background_tasks.add_task(
                save_conversation_background,
                db_session,
                request.messages,
                response_content,
                response_time
            )
            
            return ChatCompletionResponse(
                id=request_id,
                model=request.model,
                choices=[ChatCompletionChoice(
                    message=ChatMessage(role="assistant", content=response_content),
                    finish_reason="stop"
                )],
                usage={
                    "prompt_tokens": len(last_user_message.split()),
                    "completion_tokens": len(response_content.split()),
                    "total_tokens": len(last_user_message.split()) + len(response_content.split())
                }
            )
            
    except Exception as e:
        logger.error(f"Erro no chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

async def stream_chat_response(
    request: ChatCompletionRequest,
    user_message: str,
    context: str,
    request_id: str,
    start_time: float,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession
) -> AsyncGenerator[str, None]:
    """Gerar resposta streaming para chat"""
    try:
        previous_content = ""
        
        # Gerar resposta streaming
        async for update in ai_service.generate_response_stream(
            messages=request.messages,
            context=context,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ):
            delta_content = update[len(previous_content):]
            previous_content = update
            
            if delta_content:
                chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": delta_content, "role": "assistant"},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)
        
        # Chunk final
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        
        # Salvar conversa em background
        response_time = time.time() - start_time
        background_tasks.add_task(
            save_conversation_background,
            db_session,
            request.messages,
            previous_content,
            response_time
        )
        
    except Exception as e:
        logger.error(f"Erro no streaming: {e}", exc_info=True)
        error_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {"content": f"Erro: {str(e)}"},
                "finish_reason": "error"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"

@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session)
):
    """Receber e processar feedback do usuário"""
    try:
        if not feedback_service:
            raise HTTPException(status_code=503, detail="Serviço de feedback não disponível")
        
        # Salvar feedback
        feedback_id = await feedback_service.save_feedback(
            db_session=db_session,
            message_id=feedback.message_id,
            user_id=feedback.user_id,
            rating=feedback.rating,
            comment=feedback.comment,
            feedback_type=feedback.feedback_type
        )
        
        # Processar feedback para aprendizado em background
        background_tasks.add_task(
            process_feedback_learning,
            feedback_id,
            feedback.rating,
            feedback.comment
        )
        
        return FeedbackResponse(
            feedback_id=feedback_id,
            status="success",
            message="Feedback recebido e será processado para aprendizado"
        )
        
    except Exception as e:
        logger.error(f"Erro ao processar feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge", response_model=KnowledgeResponse)
async def add_knowledge_item(
    knowledge: KnowledgeRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db_session)
):
    """Adicionar item à base de conhecimento"""
    try:
        if not knowledge_service:
            raise HTTPException(status_code=503, detail="Serviço de conhecimento não disponível")
        
        knowledge_id = await knowledge_service.add_knowledge_item(
            db_session=db_session,
            title=knowledge.title,
            content=knowledge.content,
            category=knowledge.category,
            tags=knowledge.tags,
            source=knowledge.source
        )
        
        # Gerar embeddings em background
        background_tasks.add_task(
            generate_embeddings_background,
            knowledge_id,
            knowledge.content
        )
        
        return KnowledgeResponse(
            id=knowledge_id,
            title=knowledge.title,
            content=knowledge.content,
            category=knowledge.category,
            tags=knowledge.tags,
            source=knowledge.source,
            created_at=time.time(),
            updated_at=time.time()
        )
        
    except Exception as e:
        logger.error(f"Erro ao adicionar conhecimento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge_item(
    knowledge_id: str,
    db_session: AsyncSession = Depends(get_db_session)
):
    """Recuperar item específico da base de conhecimento"""
    try:
        if not knowledge_service:
            raise HTTPException(status_code=503, detail="Serviço de conhecimento não disponível")
        
        item = await knowledge_service.get_knowledge_item(db_session, knowledge_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item de conhecimento não encontrado")
        
        return KnowledgeResponse(**item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar conhecimento: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics", response_model=SystemMetrics)
async def get_system_metrics(db_session: AsyncSession = Depends(get_db_session)):
    """Obter métricas completas do sistema"""
    try:
        if not metrics_service:
            raise HTTPException(status_code=503, detail="Serviço de métricas não disponível")
        
        metrics = await metrics_service.get_comprehensive_metrics(db_session)
        return SystemMetrics(**metrics)
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/learning-analysis")
async def get_learning_analysis(
    days: int = 7,
    db_session: AsyncSession = Depends(get_db_session)
):
    """Obter análise de aprendizado do sistema"""
    try:
        if not learning_service:
            raise HTTPException(status_code=503, detail="Serviço de aprendizado não disponível")
        
        analysis = await learning_service.get_learning_analysis(db_session, days)
        return analysis
        
    except Exception as e:
        logger.error(f"Erro na análise de aprendizado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/trigger-learning")
async def trigger_learning_session(
    background_tasks: BackgroundTasks,
    session_type: str = "comprehensive_analysis"
):
    """Disparar sessão de aprendizado manual"""
    try:
        if not learning_service:
            raise HTTPException(status_code=503, detail="Serviço de aprendizado não disponível")
        
        session_id = str(uuid.uuid4())
        
        # Disparar aprendizado em background
        background_tasks.add_task(
            trigger_learning_background,
            session_id,
            session_type
        )
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": f"Sessão de aprendizado '{session_type}' iniciada"
        }
        
    except Exception as e:
        logger.error(f"Erro ao disparar aprendizado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/system-config")
async def get_system_config(db_session: AsyncSession = Depends(get_db_session)):
    """Obter configuração atual do sistema"""
    try:
        if not database_service:
            raise HTTPException(status_code=503, detail="Serviço de banco não disponível")
        
        config = await database_service.get_system_config(db_session)
        return config
        
    except Exception as e:
        logger.error(f"Erro ao obter configuração: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/system-config")
async def update_system_config(
    config_update: SystemConfigUpdate,
    db_session: AsyncSession = Depends(get_db_session)
):
    """Atualizar configuração do sistema"""
    try:
        if not database_service:
            raise HTTPException(status_code=503, detail="Serviço de banco não disponível")
        
        await database_service.update_system_config(
            db_session, 
            config_update.config_key, 
            config_update.config_value
        )
        
        return {"status": "success", "message": "Configuração atualizada"}
        
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Funções de background tasks

async def save_conversation_background(
    db_session: AsyncSession,
    messages: List[ChatMessage],
    response_content: str,
    response_time: float
):
    """Salvar conversa no banco de dados (background task)"""
    try:
        if database_service:
            await database_service.save_conversation(
                db_session, messages, response_content, response_time
            )
        logger.info("💾 Conversa salva no banco de dados")
    except Exception as e:
        logger.error(f"Erro ao salvar conversa: {e}", exc_info=True)

async def process_feedback_learning(feedback_id: str, rating: int, comment: Optional[str]):
    """Processar feedback para aprendizado (background task)"""
    try:
        if learning_service:
            await learning_service.process_feedback_for_learning(
                feedback_id, rating, comment
            )
        logger.info(f"🧠 Feedback {feedback_id} processado para aprendizado")
    except Exception as e:
        logger.error(f"Erro ao processar feedback para aprendizado: {e}", exc_info=True)

async def generate_embeddings_background(knowledge_id: str, content: str):
    """Gerar embeddings para conhecimento (background task)"""
    try:
        if knowledge_service:
            await knowledge_service.generate_embeddings(knowledge_id, content)
        logger.info(f"🔢 Embeddings gerados para conhecimento {knowledge_id}")
    except Exception as e:
        logger.error(f"Erro ao gerar embeddings: {e}", exc_info=True)

async def trigger_learning_background(session_id: str, session_type: str):
    """Disparar sessão de aprendizado (background task)"""
    try:
        if learning_service:
            await learning_service.run_learning_session(session_id, session_type)
        logger.info(f"🎓 Sessão de aprendizado {session_id} concluída")
    except Exception as e:
        logger.error(f"Erro na sessão de aprendizado: {e}", exc_info=True)

# Endpoint para WebSocket (futuro)
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     """WebSocket para comunicação em tempo real"""
#     await websocket.accept()
#     # TODO: Implementar lógica de WebSocket

if __name__ == "__main__":
    # Configurações do servidor
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"🚀 Iniciando servidor em http://{host}:{port}")
    logger.info(f"📚 Documentação disponível em http://{host}:{port}/docs")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,  # Desabilitar reload em produção
        access_log=True,
        log_level="info"
    )