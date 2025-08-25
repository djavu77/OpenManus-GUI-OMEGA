"""
Serviço de Métricas e Monitoramento
Sistema de IA Conversacional Avançada
"""

import json
import psutil
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta

from app.logger import logger

class MetricsService:
    """Serviço para coleta e análise de métricas do sistema"""
    
    def __init__(self):
        self.metrics_retention_days = 30
        
    async def record_metric(
        self,
        db_session: AsyncSession,
        metric_name: str,
        metric_value: float,
        metric_type: str = "gauge",
        labels: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Registrar uma métrica no banco de dados"""
        try:
            await db_session.execute(text("""
                INSERT INTO performance_metrics 
                (metric_name, metric_value, metric_type, labels, context)
                VALUES (:name, :value, :type, :labels, :context)
            """), {
                "name": metric_name,
                "value": metric_value,
                "type": metric_type,
                "labels": json.dumps(labels or {}),
                "context": json.dumps(context or {})
            })
            
            await db_session.commit()
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro ao registrar métrica: {e}", exc_info=True)

    async def get_system_metrics(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Obter métricas completas do sistema"""
        try:
            metrics = {}
            
            # Métricas de conversas
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(DISTINCT c.id) as total_conversations,
                    COUNT(m.id) as total_messages,
                    COUNT(DISTINCT c.user_id) as unique_users
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.created_at >= CURRENT_DATE - INTERVAL '30 days'
            """))
            
            conv_stats = result.fetchone()
            metrics["conversations"] = {
                "total": conv_stats[0] if conv_stats else 0,
                "total_messages": conv_stats[1] if conv_stats else 0,
                "unique_users": conv_stats[2] if conv_stats else 0
            }
            
            # Métricas de feedback
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) * 100.0 / COUNT(*) as positive_rate
                FROM feedback
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            """))
            
            feedback_stats = result.fetchone()
            metrics["feedback"] = {
                "total": feedback_stats[0] if feedback_stats else 0,
                "average_rating": float(feedback_stats[1]) if feedback_stats and feedback_stats[1] else 0,
                "positive_rate": float(feedback_stats[2]) if feedback_stats and feedback_stats[2] else 0
            }
            
            # Métricas de performance
            result = await db_session.execute(text("""
                SELECT 
                    metric_name,
                    AVG(metric_value) as avg_value,
                    MAX(metric_value) as max_value,
                    MIN(metric_value) as min_value,
                    COUNT(*) as sample_count
                FROM performance_metrics
                WHERE timestamp >= CURRENT_DATE - INTERVAL '24 hours'
                AND metric_type = 'gauge'
                GROUP BY metric_name
                ORDER BY metric_name
            """))
            
            performance_metrics = {}
            for row in result.fetchall():
                performance_metrics[row[0]] = {
                    "average": float(row[1]) if row[1] else 0,
                    "maximum": float(row[2]) if row[2] else 0,
                    "minimum": float(row[3]) if row[3] else 0,
                    "samples": row[4]
                }
            
            metrics["performance"] = performance_metrics
            
            # Métricas de base de conhecimento
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(DISTINCT category) as categories,
                    AVG(confidence_score) as avg_confidence,
                    SUM(usage_count) as total_usage
                FROM knowledge_base
            """))
            
            kb_stats = result.fetchone()
            metrics["knowledge_base"] = {
                "total_items": kb_stats[0] if kb_stats else 0,
                "categories": kb_stats[1] if kb_stats else 0,
                "avg_confidence": float(kb_stats[2]) if kb_stats and kb_stats[2] else 0,
                "total_usage": kb_stats[3] if kb_stats else 0
            }
            
            # Métricas do sistema (CPU, memória, etc.)
            system_metrics = self._get_system_resource_metrics()
            metrics["system"] = system_metrics
            
            # Métricas de aprendizado
            result = await db_session.execute(text("""
                SELECT 
                    session_type,
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration
                FROM learning_sessions
                WHERE started_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY session_type
            """))
            
            learning_metrics = {}
            for row in result.fetchall():
                learning_metrics[row[0]] = {
                    "total_sessions": row[1],
                    "completed_sessions": row[2],
                    "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                    "avg_duration_seconds": float(row[3]) if row[3] else 0
                }
            
            metrics["learning"] = learning_metrics
            
            # Timestamp da coleta
            metrics["collected_at"] = datetime.now().isoformat()
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter métricas do sistema: {e}", exc_info=True)
            return {"error": str(e)}

    def _get_system_resource_metrics(self) -> Dict[str, Any]:
        """Obter métricas de recursos do sistema"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memória
            memory = psutil.virtual_memory()
            
            # Disco
            disk = psutil.disk_usage('/')
            
            # Rede (se disponível)
            try:
                network = psutil.net_io_counters()
                network_metrics = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            except:
                network_metrics = {}
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_avg": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else []
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total * 100) if disk.total > 0 else 0
                },
                "network": network_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter métricas de recursos: {e}", exc_info=True)
            return {}

    async def get_performance_trends(
        self,
        db_session: AsyncSession,
        days: int = 7
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Obter tendências de performance dos últimos dias"""
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Tendência de tempo de resposta
            result = await db_session.execute(text("""
                SELECT 
                    DATE(timestamp) as date,
                    AVG(metric_value) as avg_response_time,
                    COUNT(*) as sample_count
                FROM performance_metrics
                WHERE metric_name = 'response_time'
                AND timestamp >= :since_date
                GROUP BY DATE(timestamp)
                ORDER BY date
            """), {"since_date": since_date})
            
            response_time_trend = [
                {
                    "date": row[0].isoformat(),
                    "avg_response_time": float(row[1]) if row[1] else 0,
                    "sample_count": row[2]
                }
                for row in result.fetchall()
            ]
            
            # Tendência de satisfação do usuário
            result = await db_session.execute(text("""
                SELECT 
                    DATE(created_at) as date,
                    AVG(rating) as avg_rating,
                    COUNT(*) as feedback_count
                FROM feedback
                WHERE created_at >= :since_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """), {"since_date": since_date})
            
            satisfaction_trend = [
                {
                    "date": row[0].isoformat(),
                    "avg_rating": float(row[1]) if row[1] else 0,
                    "feedback_count": row[2]
                }
                for row in result.fetchall()
            ]
            
            return {
                "response_time": response_time_trend,
                "user_satisfaction": satisfaction_trend
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter tendências: {e}", exc_info=True)
            return {}

    async def cleanup_old_metrics(
        self,
        db_session: AsyncSession
    ):
        """Limpar métricas antigas para manter performance"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.metrics_retention_days)
            
            result = await db_session.execute(text("""
                DELETE FROM performance_metrics 
                WHERE timestamp < :cutoff_date
            """), {"cutoff_date": cutoff_date})
            
            deleted_count = result.rowcount
            await db_session.commit()
            
            if deleted_count > 0:
                logger.info(f"🧹 Removidas {deleted_count} métricas antigas")
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro na limpeza de métricas: {e}", exc_info=True)