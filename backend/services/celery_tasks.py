"""
Tarefas Celery para Processamento Assíncrono
Sistema de IA Conversacional Avançada
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List
from datetime import datetime, timedelta

from celery import current_task
from backend.services.celery_app import celery_app
from backend.database.connection import AsyncSessionLocal
from backend.services.feedback_service import FeedbackService
from backend.services.knowledge_service import KnowledgeService
from backend.services.metrics_service import MetricsService

from app.logger import logger

# Instanciar serviços
feedback_service = FeedbackService()
knowledge_service = KnowledgeService()
metrics_service = MetricsService()

@celery_app.task(bind=True, name="analyze_feedback_batch")
def analyze_feedback_batch(self):
    """Analisar lote de feedbacks para aprendizado"""
    try:
        logger.info("🧠 Iniciando análise de feedback em lote...")
        
        # Executar análise assíncrona
        result = asyncio.run(_analyze_feedback_batch_async())
        
        logger.info(f"✅ Análise de feedback concluída: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na análise de feedback: {e}", exc_info=True)
        self.retry(countdown=60, max_retries=3)

async def _analyze_feedback_batch_async():
    """Função assíncrona para análise de feedback"""
    async with AsyncSessionLocal() as session:
        try:
            # Buscar feedbacks não processados
            result = await session.execute(text("""
                SELECT id, message_id, rating, comment, feedback_type, created_at
                FROM feedback 
                WHERE processed = false
                ORDER BY created_at DESC
                LIMIT 100
            """))
            
            feedbacks = result.fetchall()
            
            if not feedbacks:
                return {"status": "no_feedback_to_process"}
            
            # Analisar feedbacks
            analysis_results = {
                "processed_count": len(feedbacks),
                "positive_feedback": 0,
                "negative_feedback": 0,
                "improvement_areas": [],
                "knowledge_updates": 0
            }
            
            feedback_ids_to_mark = []
            
            for feedback in feedbacks:
                feedback_id, message_id, rating, comment, feedback_type, created_at = feedback
                feedback_ids_to_mark.append(feedback_id)
                
                if rating >= 4:
                    analysis_results["positive_feedback"] += 1
                    
                    # Extrair conhecimento de feedback positivo
                    if comment and len(comment) > 50:
                        await knowledge_service.add_knowledge_item(
                            session,
                            title=f"Conhecimento de feedback positivo",
                            content=comment,
                            category="feedback_derived",
                            source="user_feedback",
                            confidence_score=0.8
                        )
                        analysis_results["knowledge_updates"] += 1
                        
                elif rating <= 2:
                    analysis_results["negative_feedback"] += 1
                    
                    # Analisar feedback negativo para melhorias
                    if comment:
                        improvement_area = _extract_improvement_area(comment)
                        if improvement_area:
                            analysis_results["improvement_areas"].append(improvement_area)
            
            # Marcar feedbacks como processados
            await feedback_service.mark_feedback_processed(session, feedback_ids_to_mark)
            
            # Registrar métricas da análise
            await metrics_service.record_metric(
                session,
                "feedback_analysis_processed",
                len(feedbacks),
                "counter",
                {"batch_id": str(uuid.uuid4())}
            )
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"❌ Erro na análise assíncrona de feedback: {e}", exc_info=True)
            raise

def _extract_improvement_area(comment: str) -> str:
    """Extrair área de melhoria de comentário negativo"""
    comment_lower = comment.lower()
    
    if any(word in comment_lower for word in ['lento', 'devagar', 'demora', 'tempo']):
        return "performance"
    elif any(word in comment_lower for word in ['errado', 'incorreto', 'erro', 'impreciso']):
        return "accuracy"
    elif any(word in comment_lower for word in ['confuso', 'não entendi', 'unclear', 'vago']):
        return "clarity"
    elif any(word in comment_lower for word in ['incompleto', 'faltou', 'mais detalhes']):
        return "completeness"
    else:
        return "general"

@celery_app.task(bind=True, name="optimize_model_parameters")
def optimize_model_parameters(self):
    """Otimizar parâmetros do modelo baseado em métricas"""
    try:
        logger.info("⚙️ Iniciando otimização de parâmetros do modelo...")
        
        result = asyncio.run(_optimize_model_parameters_async())
        
        logger.info(f"✅ Otimização concluída: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na otimização: {e}", exc_info=True)
        self.retry(countdown=300, max_retries=2)

async def _optimize_model_parameters_async():
    """Função assíncrona para otimização de parâmetros"""
    async with AsyncSessionLocal() as session:
        try:
            # Analisar métricas recentes
            result = await session.execute(text("""
                SELECT 
                    AVG(rating) as avg_rating,
                    COUNT(*) as feedback_count
                FROM feedback 
                WHERE created_at >= CURRENT_DATE - INTERVAL '24 hours'
            """))
            
            stats = result.fetchone()
            avg_rating = float(stats[0]) if stats and stats[0] else 3.0
            feedback_count = stats[1] if stats else 0
            
            # Determinar ajustes baseados na performance
            optimization_result = {
                "current_avg_rating": avg_rating,
                "feedback_count": feedback_count,
                "adjustments_made": []
            }
            
            # Lógica de otimização simples
            if avg_rating < 3.0 and feedback_count >= 10:
                # Rating baixo - ajustar temperatura para respostas mais conservadoras
                new_temperature = max(0.3, 0.7 - 0.1)
                optimization_result["adjustments_made"].append(
                    f"Temperatura reduzida para {new_temperature} devido a rating baixo"
                )
                
                # Atualizar configuração
                await session.execute(text("""
                    UPDATE system_config 
                    SET config_value = :value, updated_at = CURRENT_TIMESTAMP
                    WHERE config_key = 'response_temperature'
                """), {"value": json.dumps(new_temperature)})
                
            elif avg_rating > 4.0 and feedback_count >= 10:
                # Rating alto - pode aumentar criatividade
                new_temperature = min(0.9, 0.7 + 0.1)
                optimization_result["adjustments_made"].append(
                    f"Temperatura aumentada para {new_temperature} devido a rating alto"
                )
                
                await session.execute(text("""
                    UPDATE system_config 
                    SET config_value = :value, updated_at = CURRENT_TIMESTAMP
                    WHERE config_key = 'response_temperature'
                """), {"value": json.dumps(new_temperature)})
            
            await session.commit()
            
            # Registrar sessão de aprendizado
            session_id = str(uuid.uuid4())
            await session.execute(text("""
                INSERT INTO learning_sessions (id, session_type, status, input_data, output_data, completed_at)
                VALUES (:id, 'model_optimization', 'completed', :input_data, :output_data, CURRENT_TIMESTAMP)
            """), {
                "id": session_id,
                "input_data": json.dumps({"avg_rating": avg_rating, "feedback_count": feedback_count}),
                "output_data": json.dumps(optimization_result)
            })
            
            await session.commit()
            
            return optimization_result
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Erro na otimização assíncrona: {e}", exc_info=True)
            raise

@celery_app.task(bind=True, name="generate_embeddings")
def generate_embeddings(self, knowledge_id: str, content: str):
    """Gerar embeddings para item de conhecimento"""
    try:
        logger.info(f"🔢 Gerando embeddings para conhecimento {knowledge_id}...")
        
        # TODO: Implementar geração real de embeddings
        # Por enquanto, simular o processo
        
        result = {
            "knowledge_id": knowledge_id,
            "content_length": len(content),
            "embedding_dimensions": 384,  # all-MiniLM-L6-v2
            "status": "completed"
        }
        
        logger.info(f"✅ Embeddings gerados para {knowledge_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar embeddings: {e}", exc_info=True)
        self.retry(countdown=60, max_retries=3)

@celery_app.task(bind=True, name="cleanup_old_data")
def cleanup_old_data(self):
    """Limpeza de dados antigos"""
    try:
        logger.info("🧹 Iniciando limpeza de dados antigos...")
        
        result = asyncio.run(_cleanup_old_data_async())
        
        logger.info(f"✅ Limpeza concluída: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na limpeza: {e}", exc_info=True)
        self.retry(countdown=300, max_retries=2)

async def _cleanup_old_data_async():
    """Função assíncrona para limpeza de dados"""
    async with AsyncSessionLocal() as session:
        try:
            cleanup_results = {
                "conversations_archived": 0,
                "metrics_cleaned": 0,
                "sessions_cleaned": 0
            }
            
            # Arquivar conversas antigas (90+ dias sem atividade)
            cutoff_date = datetime.now() - timedelta(days=90)
            
            result = await session.execute(text("""
                UPDATE conversations 
                SET status = 'archived'
                WHERE updated_at < :cutoff_date 
                AND status = 'active'
            """), {"cutoff_date": cutoff_date})
            
            cleanup_results["conversations_archived"] = result.rowcount
            
            # Limpar métricas antigas
            await metrics_service.cleanup_old_metrics(session)
            
            # Limpar sessões de aprendizado antigas
            result = await session.execute(text("""
                DELETE FROM learning_sessions
                WHERE started_at < :cutoff_date
                AND status IN ('completed', 'failed')
            """), {"cutoff_date": cutoff_date})
            
            cleanup_results["sessions_cleaned"] = result.rowcount
            
            await session.commit()
            
            return cleanup_results
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Erro na limpeza assíncrona: {e}", exc_info=True)
            raise

@celery_app.task(bind=True, name="backup_knowledge_base")
def backup_knowledge_base(self):
    """Fazer backup da base de conhecimento"""
    try:
        logger.info("💾 Iniciando backup da base de conhecimento...")
        
        result = asyncio.run(_backup_knowledge_base_async())
        
        logger.info(f"✅ Backup concluído: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro no backup: {e}", exc_info=True)
        self.retry(countdown=600, max_retries=2)

async def _backup_knowledge_base_async():
    """Função assíncrona para backup"""
    async with AsyncSessionLocal() as session:
        try:
            # Exportar base de conhecimento
            result = await session.execute(text("""
                SELECT id, title, content, category, tags, source, confidence_score,
                       usage_count, created_at, updated_at
                FROM knowledge_base
                ORDER BY created_at DESC
            """))
            
            knowledge_items = []
            for row in result.fetchall():
                knowledge_items.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "category": row[3],
                    "tags": row[4],
                    "source": row[5],
                    "confidence_score": float(row[6]) if row[6] else 0,
                    "usage_count": row[7],
                    "created_at": row[8].isoformat(),
                    "updated_at": row[9].isoformat()
                })
            
            # Salvar backup em arquivo
            backup_filename = f"knowledge_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = f"backups/{backup_filename}"
            
            # Criar diretório de backup se não existir
            import os
            os.makedirs("backups", exist_ok=True)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "backup_date": datetime.now().isoformat(),
                    "total_items": len(knowledge_items),
                    "knowledge_base": knowledge_items
                }, f, indent=2, ensure_ascii=False)
            
            return {
                "backup_file": backup_path,
                "items_backed_up": len(knowledge_items),
                "backup_size_mb": round(os.path.getsize(backup_path) / 1024 / 1024, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no backup assíncrono: {e}", exc_info=True)
            raise

@celery_app.task(bind=True, name="analyze_performance_trends")
def analyze_performance_trends(self):
    """Analisar tendências de performance semanalmente"""
    try:
        logger.info("📊 Iniciando análise de tendências de performance...")
        
        result = asyncio.run(_analyze_performance_trends_async())
        
        logger.info(f"✅ Análise de tendências concluída: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na análise de tendências: {e}", exc_info=True)
        self.retry(countdown=1800, max_retries=2)

async def _analyze_performance_trends_async():
    """Função assíncrona para análise de tendências"""
    async with AsyncSessionLocal() as session:
        try:
            # Obter tendências dos últimos 7 dias
            trends = await metrics_service.get_performance_trends(session, days=7)
            
            # Analisar tendências de satisfação
            satisfaction_trend = trends.get("user_satisfaction", [])
            if len(satisfaction_trend) >= 3:
                recent_ratings = [day["avg_rating"] for day in satisfaction_trend[-3:]]
                avg_recent = sum(recent_ratings) / len(recent_ratings)
                
                if avg_recent < 3.0:
                    # Tendência negativa - criar alerta
                    alert_data = {
                        "type": "satisfaction_decline",
                        "severity": "high",
                        "avg_rating": avg_recent,
                        "recommendation": "Revisar qualidade das respostas e considerar ajustes no modelo"
                    }
                    
                    # Salvar alerta como métrica
                    await metrics_service.record_metric(
                        session,
                        "system_alert",
                        avg_recent,
                        "gauge",
                        {"alert_type": "satisfaction_decline"},
                        alert_data
                    )
            
            # Analisar tendências de tempo de resposta
            response_time_trend = trends.get("response_time", [])
            if len(response_time_trend) >= 3:
                recent_times = [day["avg_response_time"] for day in response_time_trend[-3:]]
                avg_recent_time = sum(recent_times) / len(recent_times)
                
                if avg_recent_time > 5.0:  # Mais de 5 segundos
                    alert_data = {
                        "type": "performance_degradation",
                        "severity": "medium",
                        "avg_response_time": avg_recent_time,
                        "recommendation": "Otimizar performance do modelo ou infraestrutura"
                    }
                    
                    await metrics_service.record_metric(
                        session,
                        "system_alert",
                        avg_recent_time,
                        "gauge",
                        {"alert_type": "performance_degradation"},
                        alert_data
                    )
            
            return {
                "trends_analyzed": len(satisfaction_trend) + len(response_time_trend),
                "alerts_generated": 0,  # TODO: contar alertas reais
                "analysis_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de tendências assíncrona: {e}", exc_info=True)
            raise

@celery_app.task(bind=True, name="process_conversation_learning")
def process_conversation_learning(self, conversation_id: str):
    """Processar aprendizado de uma conversa específica"""
    try:
        logger.info(f"🎓 Processando aprendizado da conversa {conversation_id}...")
        
        result = asyncio.run(_process_conversation_learning_async(conversation_id))
        
        logger.info(f"✅ Aprendizado processado: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro no processamento de aprendizado: {e}", exc_info=True)
        self.retry(countdown=120, max_retries=3)

async def _process_conversation_learning_async(conversation_id: str):
    """Função assíncrona para processamento de aprendizado de conversa"""
    async with AsyncSessionLocal() as session:
        try:
            # Buscar mensagens da conversa
            result = await session.execute(text("""
                SELECT m.content, m.sender, f.rating, f.comment
                FROM messages m
                LEFT JOIN feedback f ON m.id = f.message_id
                WHERE m.conversation_id = :conversation_id
                ORDER BY m.timestamp
            """), {"conversation_id": conversation_id})
            
            messages = result.fetchall()
            
            if not messages:
                return {"status": "no_messages_found"}
            
            # Analisar padrões na conversa
            user_messages = [msg for msg in messages if msg[1] == "user"]
            assistant_messages = [msg for msg in messages if msg[1] == "assistant"]
            
            # Extrair tópicos principais
            topics = _extract_conversation_topics([msg[0] for msg in user_messages])
            
            # Identificar respostas bem avaliadas
            good_responses = [
                msg for msg in messages 
                if msg[1] == "assistant" and msg[2] and msg[2] >= 4
            ]
            
            learning_result = {
                "conversation_id": conversation_id,
                "total_messages": len(messages),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "topics_identified": topics,
                "good_responses_count": len(good_responses),
                "processed_at": datetime.now().isoformat()
            }
            
            # Se há respostas bem avaliadas, extrair conhecimento
            if good_responses:
                for response in good_responses[:3]:  # Limitar a 3 melhores
                    await knowledge_service.add_knowledge_item(
                        session,
                        title=f"Resposta bem avaliada - {topics[0] if topics else 'Geral'}",
                        content=response[0],
                        category="good_responses",
                        source="conversation_learning",
                        confidence_score=0.9
                    )
                    learning_result["knowledge_items_created"] = learning_result.get("knowledge_items_created", 0) + 1
            
            return learning_result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento assíncrono de aprendizado: {e}", exc_info=True)
            raise

def _extract_conversation_topics(messages: List[str]) -> List[str]:
    """Extrair tópicos principais de uma lista de mensagens"""
    # Implementação simples - em produção, usar NLP mais avançado
    all_text = " ".join(messages).lower()
    
    # Palavras-chave comuns para categorização
    topic_keywords = {
        "tecnologia": ["python", "código", "programação", "api", "sistema"],
        "ajuda": ["como", "ajuda", "problema", "erro", "dúvida"],
        "informação": ["o que é", "explique", "definição", "conceito"],
        "configuração": ["configurar", "instalar", "setup", "config"]
    }
    
    identified_topics = []
    for topic, keywords in topic_keywords.items():
        if any(keyword in all_text for keyword in keywords):
            identified_topics.append(topic)
    
    return identified_topics[:3]  # Máximo 3 tópicos

# Configuração de monitoramento de tarefas
@celery_app.task(bind=True, name="health_check")
def health_check(self):
    """Verificação de saúde do sistema Celery"""
    return {
        "status": "healthy",
        "worker_id": self.request.id,
        "timestamp": datetime.now().isoformat()
    }