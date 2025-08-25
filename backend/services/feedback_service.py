"""
Serviço de Feedback e Aprendizado
Sistema de IA Conversacional Avançada
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from datetime import datetime, timedelta

from app.logger import logger

class FeedbackService:
    """Serviço para gerenciar feedback dos usuários e aprendizado do sistema"""
    
    def __init__(self):
        self.feedback_threshold = 3  # Mínimo de feedbacks para considerar mudanças
        
    async def save_feedback(
        self,
        db_session: AsyncSession,
        message_id: str,
        user_id: Optional[str],
        rating: int,
        comment: Optional[str] = None,
        feedback_type: str = "general"
    ) -> str:
        """Salvar feedback do usuário no banco de dados"""
        try:
            feedback_id = str(uuid.uuid4())
            
            # Obter conversation_id da mensagem
            result = await db_session.execute(text("""
                SELECT conversation_id FROM messages WHERE id = :message_id
            """), {"message_id": message_id})
            
            conversation_row = result.fetchone()
            if not conversation_row:
                raise ValueError(f"Mensagem {message_id} não encontrada")
            
            conversation_id = conversation_row[0]
            
            # Inserir feedback
            await db_session.execute(text("""
                INSERT INTO feedback (id, message_id, user_id, conversation_id, rating, comment, feedback_type)
                VALUES (:id, :message_id, :user_id, :conversation_id, :rating, :comment, :feedback_type)
            """), {
                "id": feedback_id,
                "message_id": message_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "rating": rating,
                "comment": comment,
                "feedback_type": feedback_type
            })
            
            await db_session.commit()
            
            logger.info(f"💬 Feedback salvo: {feedback_id} (rating: {rating})")
            
            # Verificar se deve processar aprendizado
            await self._check_learning_trigger(db_session, message_id)
            
            return feedback_id
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro ao salvar feedback: {e}", exc_info=True)
            raise

    async def _check_learning_trigger(self, db_session: AsyncSession, message_id: str):
        """Verificar se deve disparar processo de aprendizado"""
        try:
            # Contar feedbacks para esta mensagem
            result = await db_session.execute(text("""
                SELECT COUNT(*) FROM feedback WHERE message_id = :message_id
            """), {"message_id": message_id})
            
            feedback_count = result.fetchone()[0]
            
            if feedback_count >= self.feedback_threshold:
                logger.info(f"🎯 Threshold de feedback atingido para mensagem {message_id}")
                # TODO: Disparar tarefa Celery para aprendizado
                await self._trigger_learning_session(db_session, message_id)
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar trigger de aprendizado: {e}", exc_info=True)

    async def _trigger_learning_session(self, db_session: AsyncSession, message_id: str):
        """Disparar sessão de aprendizado baseada em feedback"""
        try:
            session_id = str(uuid.uuid4())
            
            # Criar sessão de aprendizado
            await db_session.execute(text("""
                INSERT INTO learning_sessions (id, session_type, status, input_data)
                VALUES (:id, 'feedback_analysis', 'pending', :input_data)
            """), {
                "id": session_id,
                "input_data": json.dumps({"message_id": message_id})
            })
            
            await db_session.commit()
            
            logger.info(f"🧠 Sessão de aprendizado criada: {session_id}")
            
            # TODO: Enviar para fila Celery
            # celery_app.send_task('process_feedback_learning', args=[session_id])
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar sessão de aprendizado: {e}", exc_info=True)

    async def get_feedback_analysis(
        self,
        db_session: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """Obter análise de feedback dos últimos dias"""
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Estatísticas gerais de feedback
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback,
                    COUNT(CASE WHEN comment IS NOT NULL THEN 1 END) as with_comments
                FROM feedback 
                WHERE created_at >= :since_date
            """), {"since_date": since_date})
            
            stats = result.fetchone()
            
            # Feedback por categoria
            result = await db_session.execute(text("""
                SELECT 
                    feedback_type,
                    COUNT(*) as count,
                    AVG(rating) as avg_rating
                FROM feedback 
                WHERE created_at >= :since_date
                GROUP BY feedback_type
                ORDER BY count DESC
            """), {"since_date": since_date})
            
            categories = [
                {
                    "type": row[0],
                    "count": row[1],
                    "avg_rating": float(row[2]) if row[2] else 0
                }
                for row in result.fetchall()
            ]
            
            # Comentários negativos recentes
            result = await db_session.execute(text("""
                SELECT comment, rating, created_at
                FROM feedback 
                WHERE created_at >= :since_date 
                AND rating <= 2 
                AND comment IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10
            """), {"since_date": since_date})
            
            negative_comments = [
                {
                    "comment": row[0],
                    "rating": row[1],
                    "created_at": row[2].isoformat()
                }
                for row in result.fetchall()
            ]
            
            return {
                "period_days": days,
                "total_feedback": stats[0] if stats else 0,
                "average_rating": float(stats[1]) if stats and stats[1] else 0,
                "positive_feedback": stats[2] if stats else 0,
                "negative_feedback": stats[3] if stats else 0,
                "feedback_with_comments": stats[4] if stats else 0,
                "categories": categories,
                "recent_negative_comments": negative_comments
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar feedback: {e}", exc_info=True)
            return {}

    async def get_improvement_suggestions(
        self,
        db_session: AsyncSession
    ) -> List[str]:
        """Gerar sugestões de melhoria baseadas no feedback"""
        try:
            suggestions = []
            
            # Analisar feedback negativo
            result = await db_session.execute(text("""
                SELECT comment, rating
                FROM feedback 
                WHERE rating <= 2 
                AND comment IS NOT NULL
                AND created_at >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 20
            """))
            
            negative_feedback = result.fetchall()
            
            if len(negative_feedback) > 5:
                suggestions.append(
                    f"Alto volume de feedback negativo ({len(negative_feedback)} nos últimos 7 dias). "
                    "Revisar qualidade das respostas."
                )
            
            # Analisar padrões nos comentários
            common_issues = {}
            for comment, rating in negative_feedback:
                if comment:
                    # Análise simples de palavras-chave
                    comment_lower = comment.lower()
                    if any(word in comment_lower for word in ['lento', 'devagar', 'demora']):
                        common_issues['performance'] = common_issues.get('performance', 0) + 1
                    if any(word in comment_lower for word in ['errado', 'incorreto', 'erro']):
                        common_issues['accuracy'] = common_issues.get('accuracy', 0) + 1
                    if any(word in comment_lower for word in ['confuso', 'não entendi', 'unclear']):
                        common_issues['clarity'] = common_issues.get('clarity', 0) + 1
            
            # Gerar sugestões baseadas nos problemas identificados
            for issue, count in common_issues.items():
                if count >= 3:
                    if issue == 'performance':
                        suggestions.append("Otimizar tempo de resposta do sistema")
                    elif issue == 'accuracy':
                        suggestions.append("Melhorar precisão das respostas através de treinamento adicional")
                    elif issue == 'clarity':
                        suggestions.append("Aprimorar clareza e estrutura das respostas")
            
            # Verificar taxa de feedback positivo
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) * 100.0 / COUNT(*) as positive_rate
                FROM feedback 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            """))
            
            positive_rate = result.fetchone()
            if positive_rate and positive_rate[0] and positive_rate[0] < 70:
                suggestions.append(
                    f"Taxa de feedback positivo baixa ({positive_rate[0]:.1f}%). "
                    "Considerar ajustes no modelo ou prompts."
                )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sugestões: {e}", exc_info=True)
            return ["Erro ao analisar feedback para sugestões"]

    async def mark_feedback_processed(
        self,
        db_session: AsyncSession,
        feedback_ids: List[str]
    ):
        """Marcar feedbacks como processados"""
        try:
            if not feedback_ids:
                return
            
            placeholders = ','.join([f':id_{i}' for i in range(len(feedback_ids))])
            params = {f'id_{i}': feedback_id for i, feedback_id in enumerate(feedback_ids)}
            
            await db_session.execute(text(f"""
                UPDATE feedback 
                SET processed = true 
                WHERE id IN ({placeholders})
            """), params)
            
            await db_session.commit()
            
            logger.info(f"✅ {len(feedback_ids)} feedbacks marcados como processados")
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro ao marcar feedbacks como processados: {e}", exc_info=True)
            raise