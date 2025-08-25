"""
Serviço de Gerenciamento de Base de Conhecimento
Sistema de IA Conversacional Avançada
"""

import uuid
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime

from app.logger import logger

class KnowledgeService:
    """Serviço para gerenciar a base de conhecimento do sistema"""
    
    def __init__(self):
        self.max_knowledge_items = 10000
        self.similarity_threshold = 0.7
        
    async def add_knowledge_item(
        self,
        db_session: AsyncSession,
        title: str,
        content: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: str = "api",
        confidence_score: float = 1.0
    ) -> str:
        """Adicionar novo item à base de conhecimento"""
        try:
            knowledge_id = str(uuid.uuid4())
            chromadb_id = str(uuid.uuid4())
            
            # Inserir no PostgreSQL
            await db_session.execute(text("""
                INSERT INTO knowledge_base 
                (id, title, content, category, tags, source, confidence_score, chromadb_id, metadata)
                VALUES (:id, :title, :content, :category, :tags, :source, :confidence_score, :chromadb_id, :metadata)
            """), {
                "id": knowledge_id,
                "title": title,
                "content": content,
                "category": category,
                "tags": tags or [],
                "source": source,
                "confidence_score": confidence_score,
                "chromadb_id": chromadb_id,
                "metadata": json.dumps({
                    "created_by": "system",
                    "content_length": len(content),
                    "word_count": len(content.split())
                })
            })
            
            await db_session.commit()
            
            logger.info(f"📚 Conhecimento adicionado: {knowledge_id} - {title}")
            
            # TODO: Gerar embeddings no ChromaDB
            # await self._generate_embeddings(chromadb_id, content)
            
            return knowledge_id
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro ao adicionar conhecimento: {e}", exc_info=True)
            raise

    async def get_knowledge_item(
        self,
        db_session: AsyncSession,
        knowledge_id: str
    ) -> Optional[Dict[str, Any]]:
        """Recuperar item específico da base de conhecimento"""
        try:
            result = await db_session.execute(text("""
                SELECT id, title, content, category, tags, source, confidence_score,
                       usage_count, last_used_at, created_at, updated_at, metadata
                FROM knowledge_base 
                WHERE id = :knowledge_id
            """), {"knowledge_id": knowledge_id})
            
            row = result.fetchone()
            if not row:
                return None
            
            # Incrementar contador de uso
            await db_session.execute(text("""
                UPDATE knowledge_base 
                SET usage_count = usage_count + 1, last_used_at = CURRENT_TIMESTAMP
                WHERE id = :knowledge_id
            """), {"knowledge_id": knowledge_id})
            
            await db_session.commit()
            
            return {
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "category": row[3],
                "tags": row[4],
                "source": row[5],
                "confidence_score": float(row[6]) if row[6] else 0,
                "usage_count": row[7],
                "last_used_at": row[8].isoformat() if row[8] else None,
                "created_at": row[9].isoformat(),
                "updated_at": row[10].isoformat(),
                "metadata": row[11] if row[11] else {}
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar conhecimento: {e}", exc_info=True)
            return None

    async def search_relevant_context(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None
    ) -> str:
        """Buscar contexto relevante na base de conhecimento"""
        try:
            # TODO: Implementar busca semântica real com ChromaDB
            # Por enquanto, busca textual simples
            
            # Construir query SQL com filtros
            where_clause = "WHERE content ILIKE :query"
            params = {"query": f"%{query}%", "limit": limit}
            
            if category:
                where_clause += " AND category = :category"
                params["category"] = category
            
            # Buscar itens relevantes
            sql_query = f"""
                SELECT title, content, category, confidence_score, usage_count
                FROM knowledge_base 
                {where_clause}
                ORDER BY confidence_score DESC, usage_count DESC
                LIMIT :limit
            """
            
            # Usar uma nova sessão para esta consulta
            from backend.database.connection import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                result = await session.execute(text(sql_query), params)
                rows = result.fetchall()
            
            if not rows:
                return ""
            
            # Formatar contexto
            context_parts = []
            for row in rows:
                title, content, category, confidence, usage = row
                context_parts.append(f"**{title}** ({category or 'Geral'}):\n{content[:500]}...")
            
            context = "\n\n".join(context_parts)
            logger.info(f"🔍 Contexto relevante encontrado: {len(rows)} itens")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar contexto relevante: {e}", exc_info=True)
            return ""

    async def update_knowledge_from_feedback(
        self,
        db_session: AsyncSession,
        feedback_data: Dict[str, Any]
    ):
        """Atualizar base de conhecimento baseado em feedback"""
        try:
            # Analisar feedback para extrair conhecimento
            if feedback_data.get("rating", 0) >= 4 and feedback_data.get("comment"):
                comment = feedback_data["comment"]
                
                # Extrair possível conhecimento do comentário positivo
                if len(comment) > 50:  # Comentários substanciais
                    knowledge_id = await self.add_knowledge_item(
                        db_session,
                        title=f"Conhecimento extraído de feedback positivo",
                        content=comment,
                        category="feedback_derived",
                        source="user_feedback",
                        confidence_score=0.8
                    )
                    
                    logger.info(f"📖 Conhecimento extraído de feedback: {knowledge_id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar conhecimento: {e}", exc_info=True)

    async def get_knowledge_stats(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Obter estatísticas da base de conhecimento"""
        try:
            # Estatísticas gerais
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(DISTINCT category) as categories_count,
                    AVG(confidence_score) as avg_confidence,
                    SUM(usage_count) as total_usage,
                    MAX(created_at) as last_added
                FROM knowledge_base
            """))
            
            stats = result.fetchone()
            
            # Itens por categoria
            result = await db_session.execute(text("""
                SELECT 
                    COALESCE(category, 'Sem Categoria') as category,
                    COUNT(*) as count,
                    AVG(confidence_score) as avg_confidence
                FROM knowledge_base
                GROUP BY category
                ORDER BY count DESC
            """))
            
            categories = [
                {
                    "category": row[0],
                    "count": row[1],
                    "avg_confidence": float(row[2]) if row[2] else 0
                }
                for row in result.fetchall()
            ]
            
            # Itens mais utilizados
            result = await db_session.execute(text("""
                SELECT title, usage_count, last_used_at
                FROM knowledge_base
                WHERE usage_count > 0
                ORDER BY usage_count DESC
                LIMIT 10
            """))
            
            most_used = [
                {
                    "title": row[0],
                    "usage_count": row[1],
                    "last_used_at": row[2].isoformat() if row[2] else None
                }
                for row in result.fetchall()
            ]
            
            return {
                "total_items": stats[0] if stats else 0,
                "categories_count": stats[1] if stats else 0,
                "average_confidence": float(stats[2]) if stats and stats[2] else 0,
                "total_usage": stats[3] if stats else 0,
                "last_added": stats[4].isoformat() if stats and stats[4] else None,
                "categories": categories,
                "most_used_items": most_used
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}", exc_info=True)
            return {}

    async def cleanup_old_knowledge(
        self,
        db_session: AsyncSession,
        days_threshold: int = 90
    ):
        """Limpar conhecimento antigo e pouco utilizado"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            
            # Identificar itens para limpeza
            result = await db_session.execute(text("""
                SELECT id, title
                FROM knowledge_base
                WHERE (last_used_at IS NULL OR last_used_at < :cutoff_date)
                AND usage_count < 5
                AND confidence_score < 0.5
                AND source != 'admin_input'
            """), {"cutoff_date": cutoff_date})
            
            items_to_remove = result.fetchall()
            
            if items_to_remove:
                # Remover itens identificados
                item_ids = [item[0] for item in items_to_remove]
                placeholders = ','.join([f':id_{i}' for i in range(len(item_ids))])
                params = {f'id_{i}': item_id for i, item_id in enumerate(item_ids)}
                
                await db_session.execute(text(f"""
                    DELETE FROM knowledge_base WHERE id IN ({placeholders})
                """), params)
                
                await db_session.commit()
                
                logger.info(f"🧹 Removidos {len(items_to_remove)} itens antigos da base de conhecimento")
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro na limpeza da base de conhecimento: {e}", exc_info=True)