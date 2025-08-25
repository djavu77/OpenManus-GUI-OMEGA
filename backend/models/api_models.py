"""
Modelos Pydantic para API do Sistema de IA Conversacional Avançada
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import time
import uuid

# Modelos base para Chat (compatibilidade OpenAI)
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str = "openmanus-tinyllama"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    user: Optional[str] = None

class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[Usage] = None

# Modelos para Feedback
class FeedbackRequest(BaseModel):
    message_id: str
    user_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5, description="Avaliação de 1 a 5")
    comment: Optional[str] = None
    feedback_type: str = "general"

class FeedbackResponse(BaseModel):
    feedback_id: str
    status: str
    message: str

# Modelos para Base de Conhecimento
class KnowledgeRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=10)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    source: str = "api"
    confidence_score: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)

class KnowledgeResponse(BaseModel):
    id: str
    title: str
    content: str
    category: Optional[str]
    tags: Optional[List[str]]
    source: str
    confidence_score: float
    usage_count: int = 0
    created_at: str
    updated_at: str
    relevance_score: Optional[float] = None

# Modelos para Métricas do Sistema
class SystemMetrics(BaseModel):
    total_conversations: int
    total_messages: int
    unique_users: int
    average_rating: float
    response_time_avg: float
    knowledge_base_size: int
    system_health_score: float
    last_updated: str

class PerformanceMetric(BaseModel):
    metric_name: str
    metric_value: float
    metric_type: str
    labels: Dict[str, str] = {}
    timestamp: str
    context: Dict[str, Any] = {}

# Modelos para Saúde do Sistema
class HealthResponse(BaseModel):
    status: str
    timestamp: float
    services: Dict[str, bool]
    version: str = "1.0.0"
    uptime_seconds: Optional[float] = None

# Modelos para Usuários
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: str

class UserLogin(BaseModel):
    username: str
    password: str

# Modelos para Conversas
class ConversationCreate(BaseModel):
    title: Optional[str] = "Nova Conversa"
    user_id: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    title: str
    user_id: Optional[str]
    status: str
    message_count: int
    avg_rating: Optional[float]
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    message_type: str
    metadata: Dict[str, Any]
    timestamp: str

# Modelos para Aprendizado
class LearningSessionRequest(BaseModel):
    session_type: str = Field(..., regex=r'^(model_optimization|knowledge_expansion|comprehensive_analysis)$')
    input_parameters: Optional[Dict[str, Any]] = {}

class LearningSessionResponse(BaseModel):
    id: str
    session_type: str
    status: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    started_at: str
    completed_at: Optional[str]
    error_message: Optional[str]

class LearningAnalysis(BaseModel):
    analysis_period_days: int
    learning_sessions: Dict[str, Dict[str, Any]]
    knowledge_evolution: List[Dict[str, Any]]
    performance_trends: Dict[str, List[Dict[str, Any]]]
    insights: List[str]
    recommendations: List[str]

# Modelos para Configuração do Sistema
class SystemConfig(BaseModel):
    auto_learning_enabled: bool = True
    feedback_threshold: int = 3
    max_context_length: int = 4096
    embedding_model: str = "all-MiniLM-L6-v2"
    response_temperature: float = 0.7
    max_knowledge_items: int = 10000
    cleanup_days: int = 90
    enable_metrics: bool = True

class SystemConfigUpdate(BaseModel):
    config_key: str
    config_value: Any
    description: Optional[str] = None

# Modelos para Análise e Relatórios
class FeedbackAnalysis(BaseModel):
    period_days: int
    total_feedback: int
    average_rating: float
    positive_feedback: int
    negative_feedback: int
    feedback_with_comments: int
    categories: List[Dict[str, Any]]
    recent_negative_comments: List[Dict[str, Any]]
    improvement_suggestions: List[str]

class KnowledgeStats(BaseModel):
    total_items: int
    categories_count: int
    average_confidence: float
    total_usage: int
    last_added: Optional[str]
    categories: List[Dict[str, Any]]
    most_used_items: List[Dict[str, Any]]

class SystemReport(BaseModel):
    report_id: str
    report_type: str
    generated_at: str
    period_start: str
    period_end: str
    summary: Dict[str, Any]
    detailed_analysis: Dict[str, Any]
    recommendations: List[str]

# Modelos para Busca e Filtros
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    search_type: str = Field(default="knowledge", regex=r'^(knowledge|conversations|feedback)$')
    filters: Optional[Dict[str, Any]] = {}
    limit: int = Field(default=10, ge=1, le=100)

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    relevance_score: float
    source: str
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    query: str
    search_type: str
    total_results: int
    results: List[SearchResult]
    search_time_ms: float

# Modelos para Monitoramento
class AlertRule(BaseModel):
    rule_name: str
    metric_name: str
    threshold_value: float
    comparison_operator: str = Field(..., regex=r'^(gt|lt|eq|gte|lte)$')
    alert_message: str
    is_active: bool = True

class SystemAlert(BaseModel):
    id: str
    rule_name: str
    alert_message: str
    metric_value: float
    threshold_value: float
    severity: str = Field(..., regex=r'^(low|medium|high|critical)$')
    created_at: str
    resolved_at: Optional[str] = None

# Modelos para Backup e Restauração
class BackupRequest(BaseModel):
    backup_type: str = Field(..., regex=r'^(full|incremental|knowledge_only)$')
    include_conversations: bool = True
    include_feedback: bool = True
    include_knowledge: bool = True

class BackupResponse(BaseModel):
    backup_id: str
    backup_type: str
    file_path: str
    file_size_mb: float
    items_backed_up: int
    created_at: str

# Modelos para Integração Externa
class ExternalIntegrationConfig(BaseModel):
    integration_name: str
    integration_type: str
    endpoint_url: str
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = {}
    is_active: bool = True

class WebhookEvent(BaseModel):
    event_type: str
    event_data: Dict[str, Any]
    source: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Modelos para Análise de Sentimento
class SentimentAnalysisRequest(BaseModel):
    text: str
    include_emotions: bool = False

class SentimentAnalysisResponse(BaseModel):
    text: str
    sentiment: str = Field(..., regex=r'^(positive|negative|neutral)$')
    confidence: float = Field(..., ge=0.0, le=1.0)
    emotions: Optional[Dict[str, float]] = None

# Modelos para Exportação de Dados
class DataExportRequest(BaseModel):
    export_type: str = Field(..., regex=r'^(conversations|feedback|knowledge|metrics|full)$')
    date_range: Optional[Dict[str, str]] = None
    format: str = Field(default="json", regex=r'^(json|csv|xlsx)$')
    filters: Optional[Dict[str, Any]] = {}

class DataExportResponse(BaseModel):
    export_id: str
    export_type: str
    file_path: str
    file_size_mb: float
    records_exported: int
    created_at: str