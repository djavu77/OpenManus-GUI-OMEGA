-- Schema do Banco de Dados PostgreSQL
-- Sistema de IA Conversacional Avançada

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
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'Nova Conversa',
    status VARCHAR(20) DEFAULT 'active', -- active, archived, deleted
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Mensagens (Histórico da Conversa)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text', -- text, image, file, etc.
    metadata JSONB DEFAULT '{}', -- tokens, response_time, model_version, etc.
    parent_message_id UUID REFERENCES messages(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    feedback_type VARCHAR(50) DEFAULT 'general', -- general, accuracy, helpfulness, etc.
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
    source VARCHAR(255) NOT NULL, -- 'user_feedback', 'external_doc', 'admin_input', 'auto_generated'
    confidence_score FLOAT DEFAULT 1.0,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Referência ao embedding no ChromaDB
    chromadb_id UUID UNIQUE,
    -- Metadados adicionais
    metadata JSONB DEFAULT '{}'
);

-- Tabela de Métricas de Performance
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- counter, gauge, histogram
    labels JSONB DEFAULT '{}', -- Para dimensões adicionais
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    context JSONB DEFAULT '{}'
);

-- Tabela de Sessões de Aprendizado
CREATE TABLE IF NOT EXISTS learning_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_type VARCHAR(50) NOT NULL, -- 'feedback_analysis', 'model_optimization', 'knowledge_update'
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
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

-- Índices para otimização de performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);

CREATE INDEX IF NOT EXISTS idx_feedback_message_id ON feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_processed ON feedback(processed);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_tags ON knowledge_base USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_source ON knowledge_base(source);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_confidence ON knowledge_base(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_usage ON knowledge_base(usage_count DESC);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_name_timestamp ON performance_metrics(metric_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_type ON performance_metrics(metric_type);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_type ON learning_sessions(session_type);
CREATE INDEX IF NOT EXISTS idx_learning_sessions_status ON learning_sessions(status);
CREATE INDEX IF NOT EXISTS idx_learning_sessions_started_at ON learning_sessions(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key);
CREATE INDEX IF NOT EXISTS idx_system_config_active ON system_config(is_active);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- Triggers para atualização automática de timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar triggers nas tabelas relevantes
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Inserir configurações padrão do sistema
INSERT INTO system_config (config_key, config_value, description) VALUES
('auto_learning_enabled', 'true', 'Habilitar aprendizado automático baseado em feedback'),
('feedback_threshold', '3', 'Número mínimo de feedbacks para considerar mudanças'),
('max_context_length', '4096', 'Comprimento máximo do contexto para o modelo'),
('embedding_model', '"all-MiniLM-L6-v2"', 'Modelo para geração de embeddings'),
('response_temperature', '0.7', 'Temperatura padrão para geração de respostas'),
('max_knowledge_items', '10000', 'Número máximo de itens na base de conhecimento'),
('cleanup_old_conversations_days', '90', 'Dias para manter conversas antigas'),
('enable_metrics_collection', 'true', 'Habilitar coleta de métricas de performance')
ON CONFLICT (config_key) DO NOTHING;

-- Criar usuário administrador padrão (senha: admin123)
INSERT INTO users (username, email, password_hash, is_admin) VALUES
('admin', 'admin@sistema-ia.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6hsxq5/Qe.', true)
ON CONFLICT (username) DO NOTHING;

-- Views úteis para análise
CREATE OR REPLACE VIEW conversation_stats AS
SELECT 
    c.id,
    c.title,
    c.user_id,
    u.username,
    COUNT(m.id) as message_count,
    AVG(f.rating) as avg_rating,
    COUNT(f.id) as feedback_count,
    c.created_at,
    c.updated_at
FROM conversations c
LEFT JOIN users u ON c.user_id = u.id
LEFT JOIN messages m ON c.id = m.conversation_id
LEFT JOIN feedback f ON c.id = f.conversation_id
GROUP BY c.id, c.title, c.user_id, u.username, c.created_at, c.updated_at;

CREATE OR REPLACE VIEW daily_metrics AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_interactions,
    AVG(CASE WHEN metric_name = 'response_time' THEN metric_value END) as avg_response_time,
    COUNT(DISTINCT labels->>'user_id') as unique_users
FROM performance_metrics 
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Comentários nas tabelas
COMMENT ON TABLE users IS 'Usuários do sistema de IA conversacional';
COMMENT ON TABLE conversations IS 'Conversas entre usuários e o sistema de IA';
COMMENT ON TABLE messages IS 'Mensagens individuais dentro das conversas';
COMMENT ON TABLE feedback IS 'Feedback dos usuários sobre as respostas do sistema';
COMMENT ON TABLE knowledge_base IS 'Base de conhecimento do sistema para aprendizado';
COMMENT ON TABLE performance_metrics IS 'Métricas de performance e uso do sistema';
COMMENT ON TABLE learning_sessions IS 'Sessões de aprendizado e otimização do sistema';
COMMENT ON TABLE system_config IS 'Configurações globais do sistema';
COMMENT ON TABLE audit_logs IS 'Logs de auditoria para rastreamento de ações';