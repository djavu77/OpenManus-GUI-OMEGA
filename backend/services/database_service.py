"""
Serviço de Banco de Dados - PostgreSQL
Sistema de IA Conversacional Avançada
"""

import uuid
import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, MetaData, Table, Column, String, DateTime, Integer, Float, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base

from app.logger import logger
from models.api_models import ChatMessage

# Base para modelos SQLAlchemy
Base = declarative_base()

class DatabaseService:
    """Serviço principal para gerenciamento do banco de dados PostgreSQL"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        self.metadata = MetaData()
        
    async def initialize(self):
        """Inicializar conexão com banco de dados"""
        try:
            logger.info("🗄️ Inicializando serviço de banco de dados...")
            
            # Criar engine assíncrono
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # Criar session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Verificar conexão
            await self.health_check()
            
            # Criar schema se necessário
            await self.create_schema()
            
            # Inserir configurações padrão
            await self.insert_default_config()
            
            logger.info("✅ Serviço de banco de dados inicializado")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar banco de dados: {e}", exc_info=True)
            raise
    
    async def create_schema(self):
        """Criar schema do banco de dados"""
        try:
            logger.info("📋 Criando schema do banco de dados...")
            
            schema_sql = """
            -- Extensões necessárias
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            CREATE EXTENSION IF NOT EXISTS "pg_trgm";
            
            -- Tabela de Usuários
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT true,
                is_admin BOOLEAN DEFAULT false,
                preferences JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Tabela de Conversas
            CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL DEFAULT 'Nova Conversa',
                status VARCHAR(20) DEFAULT 'active',
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Tabela de Mensagens
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                sender VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                message_type VARCHAR(50) DEFAULT 'text',
                metadata JSONB DEFAULT '{}',
                parent_message_id UUID REFERENCES messages(id),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Tabela de Feedback
            CREATE TABLE IF NOT EXISTS feedback (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                feedback_type VARCHAR(50) DEFAULT 'general',
                processed BOOLEAN DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Tabela de Base de Conhecimento
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(100),
                tags TEXT[],
                source VARCHAR(255) NOT NULL,
                confidence_score FLOAT DEFAULT 1.0,
                usage_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                chromadb_id UUID UNIQUE,
                metadata JSONB DEFAULT '{}'
            );
            
            -- Tabela de Métricas de Performance
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                metric_name VARCHAR(100) NOT NULL,
                metric_value NUMERIC NOT NULL,
                metric_type VARCHAR(50) NOT NULL,
                labels JSONB DEFAULT '{}',
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                context JSONB DEFAULT '{}'
            );
            
            -- Tabela de Sessões de Aprendizado
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                session_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                input_data JSONB,
                output_data JSONB,
                metrics JSONB DEFAULT '{}',
                started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP WITH TIME ZONE,
                error_message TEXT
            );
            
            -- Tabela de Configurações do Sistema
            CREATE TABLE IF NOT EXISTS system_config (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value JSONB NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Tabela de Logs de Auditoria
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID REFERENCES users(id),
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50) NOT NULL,
                resource_id UUID,
                old_values JSONB,
                new_values JSONB,
                ip_address INET,
                user_agent TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # Executar schema
            async with self.engine.begin() as conn:
                await conn.execute(text(schema_sql))
            
            # Criar índices
            await self.create_indexes()
            
            logger.info("✅ Schema criado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar schema: {e}", exc_info=True)
            raise
    
    async def create_indexes(self):
        """Criar índices para otimização de performance"""
        try:
            indexes_sql = """
            -- Índices para otimização
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_feedback_message_id ON feedback(message_id);
            CREATE INDEX IF NOT EXISTS idx_feedback_processed ON feedback(processed);
            CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base(category);
            CREATE INDEX IF NOT EXISTS idx_knowledge_base_tags ON knowledge_base USING GIN(tags);
            CREATE INDEX IF NOT EXISTS idx_performance_metrics_name_timestamp ON performance_metrics(metric_name, timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_learning_sessions_type ON learning_sessions(session_type);
            CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
            """
            
            async with self.engine.begin() as conn:
                await conn.execute(text(indexes_sql))
            
            logger.info("✅ Índices criados com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar índices: {e}", exc_info=True)
    
    async def insert_default_config(self):
        """Inserir configurações padrão do sistema"""
        try:
            async with self.session_factory() as session:
                # Verificar se já existem configurações
                result = await session.execute(text("SELECT COUNT(*) FROM system_config"))
                count = result.scalar()
                
                if count == 0:
                    logger.info("📝 Inserindo configurações padrão...")
                    
                    default_configs = [
                        ("auto_learning_enabled", True, "Habilitar aprendizado automático"),
                        ("feedback_threshold", 3, "Número mínimo de feedbacks para mudanças"),
                        ("max_context_length", 4096, "Comprimento máximo do contexto"),
                        ("embedding_model", "all-MiniLM-L6-v2", "Modelo para embeddings"),
                        ("response_temperature", 0.7, "Temperatura padrão para respostas"),
                        ("max_knowledge_items", 10000, "Máximo de itens na base de conhecimento"),
                        ("cleanup_days", 90, "Dias para manter dados antigos"),
                        ("enable_metrics", True, "Habilitar coleta de métricas")
                    ]
                    
                    for key, value, description in default_configs:
                        await session.execute(text("""
                            INSERT INTO system_config (config_key, config_value, description)
                            VALUES (:key, :value, :description)
                        """), {
                            "key": key,
                            "value": json.dumps(value),
                            "description": description
                        })
                    
                    # Criar usuário admin padrão
                    await session.execute(text("""
                        INSERT INTO users (username, email, password_hash, is_admin)
                        VALUES ('admin', 'admin@sistema-ia.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6hsxq5/Qe.', true)
                        ON CONFLICT (username) DO NOTHING
                    """))
                    
                    await session.commit()
                    logger.info("✅ Configurações padrão inseridas")
                
        except Exception as e:
            logger.error(f"❌ Erro ao inserir configurações padrão: {e}", exc_info=True)
    
    async def save_conversation(
        self,
        db_session: AsyncSession,
        messages: List[ChatMessage],
        response_content: str,
        response_time: float,
        user_id: Optional[str] = None
    ):
        """Salvar conversa completa no banco"""
        try:
            # Criar conversa se não existir
            conversation_id = str(uuid.uuid4())
            
            await db_session.execute(text("""
                INSERT INTO conversations (id, user_id, title, metadata)
                VALUES (:id, :user_id, :title, :metadata)
            """), {
                "id": conversation_id,
                "user_id": user_id,
                "title": f"Conversa {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                "metadata": json.dumps({"response_time": response_time})
            })
            
            # Salvar mensagens
            for i, msg in enumerate(messages):
                message_id = str(uuid.uuid4())
                await db_session.execute(text("""
                    INSERT INTO messages (id, conversation_id, sender, content, metadata)
                    VALUES (:id, :conversation_id, :sender, :content, :metadata)
                """), {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "sender": msg.role,
                    "content": msg.content,
                    "metadata": json.dumps({"order": i})
                })
            
            # Salvar resposta do assistente
            response_id = str(uuid.uuid4())
            await db_session.execute(text("""
                INSERT INTO messages (id, conversation_id, sender, content, metadata)
                VALUES (:id, :conversation_id, :sender, :content, :metadata)
            """), {
                "id": response_id,
                "conversation_id": conversation_id,
                "sender": "assistant",
                "content": response_content,
                "metadata": json.dumps({
                    "response_time": response_time,
                    "order": len(messages)
                })
            })
            
            await db_session.commit()
            logger.info(f"💾 Conversa salva: {conversation_id}")
            
            return conversation_id
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro ao salvar conversa: {e}", exc_info=True)
            raise
    
    async def get_system_config(self, db_session: AsyncSession) -> Dict[str, Any]:
        """Obter configuração atual do sistema"""
        try:
            result = await db_session.execute(text("""
                SELECT config_key, config_value, description, is_active
                FROM system_config
                WHERE is_active = true
                ORDER BY config_key
            """))
            
            config = {}
            for row in result.fetchall():
                key, value, description, is_active = row
                config[key] = {
                    "value": json.loads(value) if value else None,
                    "description": description,
                    "is_active": is_active
                }
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter configuração: {e}", exc_info=True)
            return {}
    
    async def update_system_config(
        self, 
        db_session: AsyncSession, 
        config_key: str, 
        config_value: Any
    ):
        """Atualizar configuração do sistema"""
        try:
            await db_session.execute(text("""
                UPDATE system_config 
                SET config_value = :value, updated_at = CURRENT_TIMESTAMP
                WHERE config_key = :key
            """), {
                "key": config_key,
                "value": json.dumps(config_value)
            })
            
            await db_session.commit()
            logger.info(f"⚙️ Configuração atualizada: {config_key} = {config_value}")
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"❌ Erro ao atualizar configuração: {e}", exc_info=True)
            raise
    
    async def get_conversation_history(
        self, 
        db_session: AsyncSession, 
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Obter histórico de conversas"""
        try:
            where_clause = "WHERE c.user_id = :user_id" if user_id else ""
            
            result = await db_session.execute(text(f"""
                SELECT 
                    c.id, c.title, c.status, c.created_at, c.updated_at,
                    COUNT(m.id) as message_count,
                    AVG(f.rating) as avg_rating
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                LEFT JOIN feedback f ON c.id = f.conversation_id
                {where_clause}
                GROUP BY c.id, c.title, c.status, c.created_at, c.updated_at
                ORDER BY c.updated_at DESC
                LIMIT :limit
            """), {"user_id": user_id, "limit": limit})
            
            conversations = []
            for row in result.fetchall():
                conversations.append({
                    "id": row[0],
                    "title": row[1],
                    "status": row[2],
                    "created_at": row[3].isoformat(),
                    "updated_at": row[4].isoformat(),
                    "message_count": row[5] or 0,
                    "avg_rating": float(row[6]) if row[6] else None
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter histórico: {e}", exc_info=True)
            return []
    
    async def get_conversation_messages(
        self, 
        db_session: AsyncSession, 
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Obter mensagens de uma conversa específica"""
        try:
            result = await db_session.execute(text("""
                SELECT id, sender, content, message_type, metadata, timestamp
                FROM messages
                WHERE conversation_id = :conversation_id
                ORDER BY timestamp ASC
            """), {"conversation_id": conversation_id})
            
            messages = []
            for row in result.fetchall():
                messages.append({
                    "id": row[0],
                    "sender": row[1],
                    "content": row[2],
                    "message_type": row[3],
                    "metadata": row[4] if row[4] else {},
                    "timestamp": row[5].isoformat()
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter mensagens: {e}", exc_info=True)
            return []
    
    async def get_system_statistics(self, db_session: AsyncSession) -> Dict[str, Any]:
        """Obter estatísticas gerais do sistema"""
        try:
            # Estatísticas de conversas
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(DISTINCT c.id) as total_conversations,
                    COUNT(m.id) as total_messages,
                    COUNT(DISTINCT c.user_id) as unique_users,
                    AVG(EXTRACT(EPOCH FROM (c.updated_at - c.created_at))) as avg_conversation_duration
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.created_at >= CURRENT_DATE - INTERVAL '30 days'
            """))
            
            conv_stats = result.fetchone()
            
            # Estatísticas de feedback
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) * 100.0 / COUNT(*) as positive_rate,
                    COUNT(CASE WHEN processed = true THEN 1 END) as processed_feedback
                FROM feedback
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            """))
            
            feedback_stats = result.fetchone()
            
            # Estatísticas da base de conhecimento
            result = await db_session.execute(text("""
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(DISTINCT category) as categories,
                    AVG(confidence_score) as avg_confidence,
                    SUM(usage_count) as total_usage
                FROM knowledge_base
            """))
            
            kb_stats = result.fetchone()
            
            return {
                "conversations": {
                    "total": conv_stats[0] if conv_stats else 0,
                    "total_messages": conv_stats[1] if conv_stats else 0,
                    "unique_users": conv_stats[2] if conv_stats else 0,
                    "avg_duration": float(conv_stats[3]) if conv_stats and conv_stats[3] else 0
                },
                "feedback": {
                    "total": feedback_stats[0] if feedback_stats else 0,
                    "average_rating": float(feedback_stats[1]) if feedback_stats and feedback_stats[1] else 0,
                    "positive_rate": float(feedback_stats[2]) if feedback_stats and feedback_stats[2] else 0,
                    "processed": feedback_stats[3] if feedback_stats else 0
                },
                "knowledge_base": {
                    "total_items": kb_stats[0] if kb_stats else 0,
                    "categories": kb_stats[1] if kb_stats else 0,
                    "avg_confidence": float(kb_stats[2]) if kb_stats and kb_stats[2] else 0,
                    "total_usage": kb_stats[3] if kb_stats else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}", exc_info=True)
            return {}
    
    async def health_check(self) -> bool:
        """Verificar saúde da conexão com banco"""
        try:
            if not self.engine:
                return False
            
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
                
        except Exception as e:
            logger.error(f"❌ Erro no health check do banco: {e}")
            return False
    
    async def cleanup(self):
        """Limpar recursos do serviço"""
        try:
            if self.engine:
                await self.engine.dispose()
                self.engine = None
            logger.info("🧹 Serviço de banco limpo")
        except Exception as e:
            logger.error(f"Erro no cleanup do banco: {e}", exc_info=True)

# Dependency para obter sessão do banco
async def get_db_session() -> AsyncSession:
    """Dependency para obter sessão do banco de dados"""
    if not database_service or not database_service.session_factory:
        raise HTTPException(status_code=503, detail="Serviço de banco não disponível")
    
    async with database_service.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()