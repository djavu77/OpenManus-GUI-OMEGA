"""
Serviço de Aprendizado Avançado
Sistema de IA Conversacional com Auto-Aprendizado
"""

import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.logger import logger

class LearningService:
    """Serviço responsável pelo auto-aprendizado e evolução contínua do sistema"""
    
    def __init__(self, database_service, knowledge_service, metrics_service, ai_service):
        self.database_service = database_service
        self.knowledge_service = knowledge_service
        self.metrics_service = metrics_service
        self.ai_service = ai_service
        
        # Configurações de aprendizado
        self.feedback_threshold = 3
        self.learning_rate = 0.1
        self.confidence_threshold = 0.7
        
        # Métricas de aprendizado
        self.learning_metrics = {
            "total_sessions": 0,
            "successful_optimizations": 0,
            "knowledge_items_created": 0,
            "model_adjustments": 0
        }
    
    async def process_feedback_for_learning(
        self, 
        feedback_id: str, 
        rating: int, 
        comment: Optional[str]
    ):
        """Processar feedback individual para aprendizado"""
        try:
            logger.info(f"🧠 Processando feedback {feedback_id} para aprendizado...")
            
            async with self.database_service.session_factory() as session:
                # Obter detalhes do feedback
                result = await session.execute(text("""
                    SELECT f.message_id, f.conversation_id, m.content as message_content
                    FROM feedback f
                    JOIN messages m ON f.message_id = m.id
                    WHERE f.id = :feedback_id
                """), {"feedback_id": feedback_id})
                
                feedback_data = result.fetchone()
                if not feedback_data:
                    logger.warning(f"Feedback {feedback_id} não encontrado")
                    return
                
                message_id, conversation_id, message_content = feedback_data
                
                # Analisar tipo de feedback
                if rating >= 4:
                    await self._process_positive_feedback(
                        session, message_content, comment, conversation_id
                    )
                elif rating <= 2:
                    await self._process_negative_feedback(
                        session, message_content, comment, conversation_id
                    )
                
                # Verificar se deve disparar otimização do modelo
                await self._check_model_optimization_trigger(session, message_id)
                
                logger.info(f"✅ Feedback {feedback_id} processado")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar feedback: {e}", exc_info=True)
    
    async def _process_positive_feedback(
        self, 
        session: AsyncSession, 
        message_content: str, 
        comment: Optional[str],
        conversation_id: str
    ):
        """Processar feedback positivo para extrair conhecimento"""
        try:
            # Extrair conhecimento de respostas bem avaliadas
            if len(message_content) > 100:  # Apenas respostas substanciais
                knowledge_id = await self.knowledge_service.add_knowledge_item(
                    db_session=session,
                    title=f"Resposta bem avaliada - {datetime.now().strftime('%d/%m/%Y')}",
                    content=message_content,
                    category="respostas_positivas",
                    source="feedback_positivo",
                    confidence_score=0.9
                )
                
                self.learning_metrics["knowledge_items_created"] += 1
                logger.info(f"📚 Conhecimento extraído de feedback positivo: {knowledge_id}")
            
            # Processar comentário positivo
            if comment and len(comment) > 20:
                await self.knowledge_service.add_knowledge_item(
                    db_session=session,
                    title=f"Insight do usuário - {datetime.now().strftime('%d/%m/%Y')}",
                    content=comment,
                    category="insights_usuarios",
                    source="comentario_positivo",
                    confidence_score=0.8
                )
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar feedback positivo: {e}", exc_info=True)
    
    async def _process_negative_feedback(
        self, 
        session: AsyncSession, 
        message_content: str, 
        comment: Optional[str],
        conversation_id: str
    ):
        """Processar feedback negativo para identificar melhorias"""
        try:
            # Analisar padrões em feedback negativo
            improvement_areas = []
            
            if comment:
                comment_lower = comment.lower()
                
                # Identificar áreas de melhoria
                if any(word in comment_lower for word in ['lento', 'devagar', 'demora']):
                    improvement_areas.append('performance')
                if any(word in comment_lower for word in ['errado', 'incorreto', 'impreciso']):
                    improvement_areas.append('accuracy')
                if any(word in comment_lower for word in ['confuso', 'não entendi', 'vago']):
                    improvement_areas.append('clarity')
                if any(word in comment_lower for word in ['incompleto', 'faltou']):
                    improvement_areas.append('completeness')
            
            # Registrar áreas de melhoria identificadas
            for area in improvement_areas:
                await self.metrics_service.record_system_metric(
                    f"improvement_needed_{area}",
                    1.0,
                    {"conversation_id": conversation_id, "source": "negative_feedback"}
                )
            
            # Marcar resposta para revisão
            await session.execute(text("""
                UPDATE messages 
                SET metadata = metadata || :flag
                WHERE id = (
                    SELECT message_id FROM feedback WHERE conversation_id = :conv_id
                )
            """), {
                "flag": json.dumps({"needs_review": True, "improvement_areas": improvement_areas}),
                "conv_id": conversation_id
            })
            
            logger.info(f"🔍 Feedback negativo analisado. Áreas de melhoria: {improvement_areas}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar feedback negativo: {e}", exc_info=True)
    
    async def _check_model_optimization_trigger(self, session: AsyncSession, message_id: str):
        """Verificar se deve disparar otimização do modelo"""
        try:
            # Contar feedbacks para esta mensagem
            result = await session.execute(text("""
                SELECT COUNT(*), AVG(rating)
                FROM feedback 
                WHERE message_id = :message_id
            """), {"message_id": message_id})
            
            count, avg_rating = result.fetchone()
            
            if count >= self.feedback_threshold:
                logger.info(f"🎯 Threshold atingido para mensagem {message_id}. Disparando otimização...")
                
                # Criar sessão de aprendizado
                session_id = str(uuid.uuid4())
                await session.execute(text("""
                    INSERT INTO learning_sessions (id, session_type, status, input_data)
                    VALUES (:id, 'model_optimization', 'pending', :input_data)
                """), {
                    "id": session_id,
                    "input_data": json.dumps({
                        "trigger_message_id": message_id,
                        "feedback_count": count,
                        "avg_rating": float(avg_rating) if avg_rating else 0
                    })
                })
                
                await session.commit()
                
                # Disparar otimização assíncrona
                asyncio.create_task(self.run_learning_session(session_id, "model_optimization"))
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar trigger de otimização: {e}", exc_info=True)
    
    async def run_learning_session(self, session_id: str, session_type: str):
        """Executar sessão de aprendizado"""
        try:
            logger.info(f"🎓 Iniciando sessão de aprendizado: {session_id} ({session_type})")
            
            async with self.database_service.session_factory() as session:
                # Marcar sessão como em execução
                await session.execute(text("""
                    UPDATE learning_sessions 
                    SET status = 'running', started_at = CURRENT_TIMESTAMP
                    WHERE id = :session_id
                """), {"session_id": session_id})
                await session.commit()
                
                # Executar tipo específico de aprendizado
                if session_type == "model_optimization":
                    result = await self._run_model_optimization(session, session_id)
                elif session_type == "knowledge_expansion":
                    result = await self._run_knowledge_expansion(session, session_id)
                elif session_type == "comprehensive_analysis":
                    result = await self._run_comprehensive_analysis(session, session_id)
                else:
                    result = {"error": f"Tipo de sessão desconhecido: {session_type}"}
                
                # Atualizar sessão com resultado
                await session.execute(text("""
                    UPDATE learning_sessions 
                    SET status = :status, completed_at = CURRENT_TIMESTAMP, output_data = :output
                    WHERE id = :session_id
                """), {
                    "session_id": session_id,
                    "status": "completed" if "error" not in result else "failed",
                    "output": json.dumps(result)
                })
                await session.commit()
                
                self.learning_metrics["total_sessions"] += 1
                if "error" not in result:
                    self.learning_metrics["successful_optimizations"] += 1
                
                logger.info(f"✅ Sessão de aprendizado {session_id} concluída")
                
        except Exception as e:
            logger.error(f"❌ Erro na sessão de aprendizado {session_id}: {e}", exc_info=True)
            
            # Marcar sessão como falhada
            try:
                async with self.database_service.session_factory() as session:
                    await session.execute(text("""
                        UPDATE learning_sessions 
                        SET status = 'failed', completed_at = CURRENT_TIMESTAMP, error_message = :error
                        WHERE id = :session_id
                    """), {"session_id": session_id, "error": str(e)})
                    await session.commit()
            except:
                pass
    
    async def _run_model_optimization(self, session: AsyncSession, session_id: str) -> Dict[str, Any]:
        """Executar otimização do modelo baseada em feedback"""
        try:
            # Analisar feedback recente
            result = await session.execute(text("""
                SELECT 
                    AVG(rating) as avg_rating,
                    COUNT(*) as total_feedback,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback
                FROM feedback
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            """))
            
            stats = result.fetchone()
            if not stats:
                return {"error": "Nenhum feedback encontrado para análise"}
            
            avg_rating, total_feedback, negative_feedback, positive_feedback = stats
            
            optimization_result = {
                "session_id": session_id,
                "analysis": {
                    "avg_rating": float(avg_rating) if avg_rating else 0,
                    "total_feedback": total_feedback,
                    "negative_rate": (negative_feedback / total_feedback) if total_feedback > 0 else 0,
                    "positive_rate": (positive_feedback / total_feedback) if total_feedback > 0 else 0
                },
                "optimizations_applied": []
            }
            
            # Aplicar otimizações baseadas na análise
            if avg_rating < 3.0 and total_feedback >= 10:
                # Otimizar para respostas mais conservadoras
                await self.ai_service.optimize_model_parameters({
                    "average_rating": avg_rating,
                    "total_feedback": total_feedback,
                    "optimization_type": "conservative"
                })
                optimization_result["optimizations_applied"].append("conservative_tuning")
                self.learning_metrics["model_adjustments"] += 1
            
            elif avg_rating > 4.0 and total_feedback >= 10:
                # Pode aumentar criatividade
                await self.ai_service.optimize_model_parameters({
                    "average_rating": avg_rating,
                    "total_feedback": total_feedback,
                    "optimization_type": "creative"
                })
                optimization_result["optimizations_applied"].append("creative_tuning")
                self.learning_metrics["model_adjustments"] += 1
            
            # Analisar padrões específicos de feedback negativo
            if negative_feedback > 5:
                result = await session.execute(text("""
                    SELECT comment
                    FROM feedback
                    WHERE rating <= 2 
                    AND comment IS NOT NULL
                    AND created_at >= CURRENT_DATE - INTERVAL '7 days'
                """))
                
                negative_comments = [row[0] for row in result.fetchall()]
                patterns = self._analyze_negative_patterns(negative_comments)
                
                optimization_result["negative_patterns"] = patterns
                
                # Aplicar correções baseadas nos padrões
                for pattern in patterns:
                    if pattern == "response_length":
                        # Ajustar comprimento das respostas
                        optimization_result["optimizations_applied"].append("response_length_adjustment")
                    elif pattern == "technical_accuracy":
                        # Melhorar precisão técnica
                        optimization_result["optimizations_applied"].append("technical_accuracy_improvement")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"❌ Erro na otimização do modelo: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _run_knowledge_expansion(self, session: AsyncSession, session_id: str) -> Dict[str, Any]:
        """Executar expansão da base de conhecimento"""
        try:
            logger.info("📚 Executando expansão da base de conhecimento...")
            
            # Identificar lacunas de conhecimento
            result = await session.execute(text("""
                SELECT 
                    m.content,
                    COUNT(f.id) as feedback_count,
                    AVG(f.rating) as avg_rating
                FROM messages m
                LEFT JOIN feedback f ON m.id = f.message_id
                WHERE m.sender = 'assistant'
                AND m.timestamp >= CURRENT_DATE - INTERVAL '14 days'
                GROUP BY m.content
                HAVING COUNT(f.id) >= 2 AND AVG(f.rating) <= 2.5
                ORDER BY COUNT(f.id) DESC
                LIMIT 10
            """))
            
            problematic_responses = result.fetchall()
            
            expansion_result = {
                "session_id": session_id,
                "problematic_responses_found": len(problematic_responses),
                "knowledge_gaps_identified": [],
                "new_knowledge_items": 0
            }
            
            # Analisar respostas problemáticas para identificar lacunas
            for response_content, feedback_count, avg_rating in problematic_responses:
                gap = await self._identify_knowledge_gap(response_content)
                if gap:
                    expansion_result["knowledge_gaps_identified"].append(gap)
                    
                    # Criar item de conhecimento para preencher a lacuna
                    knowledge_id = await self.knowledge_service.add_knowledge_item(
                        db_session=session,
                        title=f"Lacuna identificada: {gap['topic']}",
                        content=gap['suggested_content'],
                        category="lacunas_identificadas",
                        source="learning_session",
                        confidence_score=0.6
                    )
                    
                    expansion_result["new_knowledge_items"] += 1
                    self.learning_metrics["knowledge_items_created"] += 1
            
            return expansion_result
            
        except Exception as e:
            logger.error(f"❌ Erro na expansão de conhecimento: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _run_comprehensive_analysis(self, session: AsyncSession, session_id: str) -> Dict[str, Any]:
        """Executar análise abrangente do sistema"""
        try:
            logger.info("🔍 Executando análise abrangente do sistema...")
            
            # Análise de tendências de performance
            result = await session.execute(text("""
                SELECT 
                    DATE(timestamp) as date,
                    AVG(metric_value) as avg_response_time,
                    COUNT(*) as request_count
                FROM performance_metrics
                WHERE metric_name = 'response_time'
                AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                LIMIT 30
            """))
            
            performance_trend = [
                {
                    "date": row[0].isoformat(),
                    "avg_response_time": float(row[1]) if row[1] else 0,
                    "request_count": row[2]
                }
                for row in result.fetchall()
            ]
            
            # Análise de satisfação do usuário
            result = await session.execute(text("""
                SELECT 
                    DATE(created_at) as date,
                    AVG(rating) as avg_rating,
                    COUNT(*) as feedback_count
                FROM feedback
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """))
            
            satisfaction_trend = [
                {
                    "date": row[0].isoformat(),
                    "avg_rating": float(row[1]) if row[1] else 0,
                    "feedback_count": row[2]
                }
                for row in result.fetchall()
            ]
            
            # Análise de tópicos mais discutidos
            result = await session.execute(text("""
                SELECT 
                    kb.category,
                    COUNT(*) as usage_count,
                    AVG(kb.confidence_score) as avg_confidence
                FROM knowledge_base kb
                WHERE kb.last_used_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY kb.category
                ORDER BY usage_count DESC
                LIMIT 10
            """))
            
            popular_topics = [
                {
                    "category": row[0] or "Sem categoria",
                    "usage_count": row[1],
                    "avg_confidence": float(row[2]) if row[2] else 0
                }
                for row in result.fetchall()
            ]
            
            # Gerar insights e recomendações
            insights = await self._generate_system_insights(
                performance_trend, satisfaction_trend, popular_topics
            )
            
            analysis_result = {
                "session_id": session_id,
                "analysis_period": "30 days",
                "performance_trend": performance_trend[-7:],  # Últimos 7 dias
                "satisfaction_trend": satisfaction_trend[-7:],
                "popular_topics": popular_topics,
                "insights": insights,
                "recommendations": await self._generate_recommendations(insights)
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Erro na análise abrangente: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _analyze_negative_patterns(self, comments: List[str]) -> List[str]:
        """Analisar padrões em comentários negativos"""
        patterns = []
        
        if not comments:
            return patterns
        
        all_comments = " ".join(comments).lower()
        
        # Detectar padrões comuns
        if any(word in all_comments for word in ['muito longo', 'extenso', 'prolixo']):
            patterns.append("response_length")
        
        if any(word in all_comments for word in ['técnico', 'complexo', 'difícil']):
            patterns.append("technical_complexity")
        
        if any(word in all_comments for word in ['impreciso', 'errado', 'incorreto']):
            patterns.append("technical_accuracy")
        
        if any(word in all_comments for word in ['vago', 'genérico', 'superficial']):
            patterns.append("response_depth")
        
        return patterns
    
    async def _identify_knowledge_gap(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Identificar lacuna de conhecimento em resposta problemática"""
        try:
            # Análise simples para identificar tópicos
            content_lower = response_content.lower()
            
            # Identificar possíveis tópicos técnicos
            technical_terms = [
                "python", "javascript", "api", "database", "sql", "machine learning",
                "ai", "algoritmo", "programação", "desenvolvimento", "sistema"
            ]
            
            identified_topics = [term for term in technical_terms if term in content_lower]
            
            if identified_topics:
                return {
                    "topic": identified_topics[0],
                    "suggested_content": f"Informações detalhadas sobre {identified_topics[0]} baseadas em feedback negativo",
                    "confidence": 0.6,
                    "source": "gap_analysis"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao identificar lacuna: {e}")
            return None
    
    async def _generate_system_insights(
        self, 
        performance_trend: List[Dict], 
        satisfaction_trend: List[Dict], 
        popular_topics: List[Dict]
    ) -> List[str]:
        """Gerar insights sobre o sistema"""
        insights = []
        
        try:
            # Análise de tendência de performance
            if len(performance_trend) >= 3:
                recent_times = [day["avg_response_time"] for day in performance_trend[-3:]]
                avg_recent = sum(recent_times) / len(recent_times)
                
                if avg_recent > 3.0:
                    insights.append("Performance degradada nos últimos dias - considerar otimização")
                elif avg_recent < 1.0:
                    insights.append("Performance excelente - sistema otimizado")
            
            # Análise de satisfação
            if len(satisfaction_trend) >= 3:
                recent_ratings = [day["avg_rating"] for day in satisfaction_trend[-3:]]
                avg_rating = sum(recent_ratings) / len(recent_ratings)
                
                if avg_rating > 4.0:
                    insights.append("Alta satisfação do usuário - manter estratégias atuais")
                elif avg_rating < 3.0:
                    insights.append("Satisfação baixa - revisar qualidade das respostas")
            
            # Análise de tópicos populares
            if popular_topics:
                top_topic = popular_topics[0]
                insights.append(f"Tópico mais popular: {top_topic['category']} ({top_topic['usage_count']} usos)")
                
                if top_topic["avg_confidence"] < 0.7:
                    insights.append(f"Baixa confiança no tópico {top_topic['category']} - necessita melhoria")
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar insights: {e}")
            return ["Erro na geração de insights"]
    
    async def _generate_recommendations(self, insights: List[str]) -> List[str]:
        """Gerar recomendações baseadas nos insights"""
        recommendations = []
        
        for insight in insights:
            if "performance degradada" in insight.lower():
                recommendations.append("Otimizar infraestrutura ou modelo para melhorar tempo de resposta")
            elif "satisfação baixa" in insight.lower():
                recommendations.append("Revisar prompts do sistema e qualidade das respostas")
            elif "baixa confiança" in insight.lower():
                recommendations.append("Expandir base de conhecimento em tópicos com baixa confiança")
            elif "alta satisfação" in insight.lower():
                recommendations.append("Documentar estratégias atuais como melhores práticas")
        
        # Recomendações gerais se nenhuma específica foi gerada
        if not recommendations:
            recommendations.append("Continuar monitoramento e coleta de feedback")
            recommendations.append("Expandir base de conhecimento com novos tópicos")
        
        return recommendations
    
    async def get_learning_analysis(self, db_session: AsyncSession, days: int = 7) -> Dict[str, Any]:
        """Obter análise de aprendizado dos últimos dias"""
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Estatísticas de sessões de aprendizado
            result = await db_session.execute(text("""
                SELECT 
                    session_type,
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration
                FROM learning_sessions
                WHERE started_at >= :since_date
                GROUP BY session_type
            """), {"since_date": since_date})
            
            session_stats = {}
            for row in result.fetchall():
                session_type, total, completed, avg_duration = row
                session_stats[session_type] = {
                    "total_sessions": total,
                    "completed_sessions": completed,
                    "success_rate": (completed / total * 100) if total > 0 else 0,
                    "avg_duration_seconds": float(avg_duration) if avg_duration else 0
                }
            
            # Análise de evolução do conhecimento
            result = await db_session.execute(text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as new_items,
                    AVG(confidence_score) as avg_confidence
                FROM knowledge_base
                WHERE created_at >= :since_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """), {"since_date": since_date})
            
            knowledge_evolution = [
                {
                    "date": row[0].isoformat(),
                    "new_items": row[1],
                    "avg_confidence": float(row[2]) if row[2] else 0
                }
                for row in result.fetchall()
            ]
            
            return {
                "analysis_period_days": days,
                "learning_sessions": session_stats,
                "knowledge_evolution": knowledge_evolution,
                "current_metrics": self.learning_metrics.copy(),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de aprendizado: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_learning_recommendations(self, db_session: AsyncSession) -> List[str]:
        """Gerar recomendações para melhorar o aprendizado"""
        try:
            recommendations = []
            
            # Verificar taxa de feedback
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(DISTINCT m.id) as total_messages,
                    COUNT(f.id) as total_feedback
                FROM messages m
                LEFT JOIN feedback f ON m.id = f.message_id
                WHERE m.sender = 'assistant'
                AND m.timestamp >= CURRENT_DATE - INTERVAL '7 days'
            """))
            
            stats = result.fetchone()
            if stats:
                total_messages, total_feedback = stats
                feedback_rate = (total_feedback / total_messages) if total_messages > 0 else 0
                
                if feedback_rate < 0.1:  # Menos de 10% de feedback
                    recommendations.append("Incentivar mais feedback dos usuários para melhorar aprendizado")
                elif feedback_rate > 0.5:  # Mais de 50% de feedback
                    recommendations.append("Excelente taxa de feedback - aproveitar para otimizações frequentes")
            
            # Verificar diversidade de tópicos
            result = await db_session.execute(text("""
                SELECT COUNT(DISTINCT category) as categories_count
                FROM knowledge_base
            """))
            
            categories_count = result.scalar() or 0
            if categories_count < 5:
                recommendations.append("Expandir diversidade de tópicos na base de conhecimento")
            
            # Verificar sessões de aprendizado recentes
            result = await db_session.execute(text("""
                SELECT COUNT(*) as recent_sessions
                FROM learning_sessions
                WHERE started_at >= CURRENT_DATE - INTERVAL '7 days'
                AND status = 'completed'
            """))
            
            recent_sessions = result.scalar() or 0
            if recent_sessions == 0:
                recommendations.append("Executar sessão de aprendizado para otimizar sistema")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar recomendações: {e}", exc_info=True)
            return ["Erro ao gerar recomendações de aprendizado"]