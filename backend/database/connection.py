"""
Conexão com Banco de Dados PostgreSQL
Sistema de IA Conversacional Avançada
"""

import os
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from pathlib import Path

from app.logger import logger

# Base para modelos SQLAlchemy
Base = declarative_base()

# Configuração do banco de dados
DATABASE_URL = os.getenv(
    "SQLALCHEMY_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/openmanus_ai"
)

# Criar engine assíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Criar session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obter sessão do banco de dados"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_database():
    """Inicializar banco de dados com schema"""
    try:
        logger.info("🗄️ Inicializando banco de dados...")
        
        # Verificar conexão
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info("✅ Conexão com PostgreSQL estabelecida")
        
        # Executar schema SQL
        schema_path = Path(__file__).parent / "schemas.sql"
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            async with engine.begin() as conn:
                # Executar schema em partes (separado por comentários principais)
                sql_statements = schema_sql.split(';')
                for statement in sql_statements:
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            await conn.execute(text(statement))
                        except Exception as e:
                            if "already exists" not in str(e).lower():
                                logger.warning(f"Erro ao executar SQL: {e}")
            
            logger.info("✅ Schema do banco de dados aplicado")
        else:
            logger.warning("⚠️ Arquivo de schema não encontrado")
        
        # Verificar tabelas criadas
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"📋 Tabelas criadas: {', '.join(tables)}")
        
        logger.info("🎉 Banco de dados inicializado com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco de dados: {e}", exc_info=True)
        raise

async def test_connection():
    """Testar conexão com o banco de dados"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ PostgreSQL conectado: {version}")
            return True
    except Exception as e:
        logger.error(f"❌ Erro de conexão com PostgreSQL: {e}")
        return False

# Função para executar migrações
async def run_migrations():
    """Executar migrações do banco de dados"""
    try:
        logger.info("🔄 Executando migrações...")
        
        # Verificar se tabela de migrações existe
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
        
        # Aplicar migrações pendentes
        migrations_dir = Path(__file__).parent / "migrations"
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob("*.sql"))
            
            for migration_file in migration_files:
                version = migration_file.stem
                
                # Verificar se migração já foi aplicada
                async with AsyncSessionLocal() as session:
                    result = await session.execute(text(
                        "SELECT 1 FROM schema_migrations WHERE version = :version"
                    ), {"version": version})
                    
                    if result.fetchone():
                        logger.info(f"⏭️ Migração {version} já aplicada")
                        continue
                
                # Aplicar migração
                logger.info(f"🔄 Aplicando migração {version}...")
                with open(migration_file, 'r', encoding='utf-8') as f:
                    migration_sql = f.read()
                
                async with engine.begin() as conn:
                    await conn.execute(text(migration_sql))
                    await conn.execute(text(
                        "INSERT INTO schema_migrations (version) VALUES (:version)"
                    ), {"version": version})
                
                logger.info(f"✅ Migração {version} aplicada")
        
        logger.info("🎉 Migrações concluídas")
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar migrações: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    # Teste de conexão
    asyncio.run(test_connection())