"""
Serviço de IA - Integração com OpenManus e TeenyTinyLlama
Sistema de IA Conversacional Avançada
"""

import asyncio
import json
import time
from typing import List, Optional, Dict, Any, AsyncGenerator

from app.agent.manus import Manus
from app.schema import AgentState, Message as AgentMessage
from app.logger import logger
from models.api_models import ChatMessage

class AIService:
    """Serviço principal para interação com IA e processamento de linguagem natural"""
    
    def __init__(self):
        self.agent: Optional[Manus] = None
        self.agent_lock = asyncio.Lock()
        self.model_config = {
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        self.performance_metrics = {
            "total_requests": 0,
            "average_response_time": 0.0,
            "success_rate": 0.0,
            "error_count": 0
        }
    
    async def initialize(self):
        """Inicializar o serviço de IA"""
        try:
            logger.info("🤖 Inicializando serviço de IA...")
            
            # Inicializar agente OpenManus
            self.agent = Manus()
            self.agent.state = AgentState.IDLE
            
            # Configurar prompts personalizados para o sistema
            self.agent.system_prompt = self._get_system_prompt()
            
            logger.info("✅ Serviço de IA inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar serviço de IA: {e}", exc_info=True)
            raise
    
    def _get_system_prompt(self) -> str:
        """Obter prompt do sistema personalizado"""
        return """
        Você é um assistente de IA conversacional avançado com capacidades de auto-aprendizado.
        
        CARACTERÍSTICAS PRINCIPAIS:
        - Aprende continuamente com feedback dos usuários
        - Mantém memória de longo prazo das interações
        - Adapta respostas baseado no contexto e histórico
        - Fornece respostas úteis, precisas e contextualmente relevantes
        
        DIRETRIZES DE COMPORTAMENTO:
        1. Seja sempre útil, respeitoso e preciso
        2. Use o contexto fornecido para enriquecer suas respostas
        3. Admita quando não souber algo e sugira alternativas
        4. Mantenha consistência com interações anteriores
        5. Adapte seu estilo de comunicação ao usuário
        
        FORMATO DE RESPOSTA:
        - Seja claro e bem estruturado
        - Use markdown quando apropriado
        - Forneça exemplos práticos quando relevante
        - Inclua fontes ou referências quando possível
        
        Lembre-se: Cada interação é uma oportunidade de aprender e melhorar.
        """
    
    async def generate_response(
        self,
        messages: List[ChatMessage],
        context: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Gerar resposta única (não-streaming)"""
        if not self.agent:
            raise RuntimeError("Serviço de IA não inicializado")
        
        async with self.agent_lock:
            try:
                start_time = time.time()
                
                # Resetar estado do agente
                self.agent.memory.messages = []
                self.agent.state = AgentState.IDLE
                self.agent.current_step = 0
                
                # Adicionar contexto se disponível
                if context:
                    context_msg = AgentMessage(
                        role="system",
                        content=f"CONTEXTO RELEVANTE DA BASE DE CONHECIMENTO:\n{context}\n\nUse este contexto para enriquecer sua resposta quando relevante."
                    )
                    self.agent.memory.add_message(context_msg)
                
                # Converter mensagens para formato do OpenManus
                for msg in messages:
                    agent_msg = AgentMessage(
                        role=msg.role,
                        content=msg.content or ""
                    )
                    self.agent.memory.add_message(agent_msg)
                
                # Obter última mensagem do usuário
                last_user_message = ""
                for msg in reversed(messages):
                    if msg.role == "user":
                        last_user_message = msg.content or ""
                        break
                
                # Gerar resposta
                final_response = ""
                async for update in self.agent.run(request=last_user_message):
                    final_response = update
                
                # Atualizar métricas de performance
                response_time = time.time() - start_time
                await self._update_performance_metrics(response_time, True)
                
                return final_response
                
            except Exception as e:
                await self._update_performance_metrics(0, False)
                logger.error(f"Erro na geração de resposta: {e}", exc_info=True)
                raise
    
    async def generate_response_stream(
        self,
        messages: List[ChatMessage],
        context: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Gerar resposta streaming"""
        if not self.agent:
            raise RuntimeError("Serviço de IA não inicializado")
        
        async with self.agent_lock:
            try:
                start_time = time.time()
                
                # Resetar estado do agente
                self.agent.memory.messages = []
                self.agent.state = AgentState.IDLE
                self.agent.current_step = 0
                
                # Adicionar contexto se disponível
                if context:
                    context_msg = AgentMessage(
                        role="system",
                        content=f"CONTEXTO RELEVANTE:\n{context}\n\nUse este contexto quando relevante."
                    )
                    self.agent.memory.add_message(context_msg)
                
                # Converter mensagens
                for msg in messages:
                    agent_msg = AgentMessage(
                        role=msg.role,
                        content=msg.content or ""
                    )
                    self.agent.memory.add_message(agent_msg)
                
                # Obter última mensagem do usuário
                last_user_message = ""
                for msg in reversed(messages):
                    if msg.role == "user":
                        last_user_message = msg.content or ""
                        break
                
                # Gerar resposta streaming
                async for update in self.agent.run(request=last_user_message):
                    yield update
                
                # Atualizar métricas
                response_time = time.time() - start_time
                await self._update_performance_metrics(response_time, True)
                
            except Exception as e:
                await self._update_performance_metrics(0, False)
                logger.error(f"Erro na geração streaming: {e}", exc_info=True)
                raise
    
    async def _update_performance_metrics(self, response_time: float, success: bool):
        """Atualizar métricas de performance do serviço"""
        try:
            self.performance_metrics["total_requests"] += 1
            
            if success:
                # Atualizar média de tempo de resposta
                current_avg = self.performance_metrics["average_response_time"]
                total_requests = self.performance_metrics["total_requests"]
                
                new_avg = ((current_avg * (total_requests - 1)) + response_time) / total_requests
                self.performance_metrics["average_response_time"] = new_avg
                
                # Atualizar taxa de sucesso
                success_count = total_requests - self.performance_metrics["error_count"]
                self.performance_metrics["success_rate"] = success_count / total_requests
            else:
                self.performance_metrics["error_count"] += 1
                success_count = self.performance_metrics["total_requests"] - self.performance_metrics["error_count"]
                self.performance_metrics["success_rate"] = success_count / self.performance_metrics["total_requests"]
            
        except Exception as e:
            logger.error(f"Erro ao atualizar métricas de performance: {e}")
    
    async def optimize_model_parameters(self, feedback_analysis: Dict[str, Any]):
        """Otimizar parâmetros do modelo baseado em análise de feedback"""
        try:
            logger.info("⚙️ Otimizando parâmetros do modelo...")
            
            avg_rating = feedback_analysis.get("average_rating", 3.0)
            feedback_count = feedback_analysis.get("total_feedback", 0)
            
            # Ajustar temperatura baseado no feedback
            if avg_rating < 3.0 and feedback_count >= 10:
                # Rating baixo - tornar respostas mais conservadoras
                self.model_config["temperature"] = max(0.3, self.model_config["temperature"] - 0.1)
                logger.info(f"🔧 Temperatura reduzida para {self.model_config['temperature']}")
                
            elif avg_rating > 4.0 and feedback_count >= 10:
                # Rating alto - pode aumentar criatividade
                self.model_config["temperature"] = min(0.9, self.model_config["temperature"] + 0.1)
                logger.info(f"🔧 Temperatura aumentada para {self.model_config['temperature']}")
            
            # Ajustar outros parâmetros baseado em padrões específicos
            negative_feedback_rate = feedback_analysis.get("negative_feedback_rate", 0)
            if negative_feedback_rate > 0.3:  # Mais de 30% de feedback negativo
                # Reduzir criatividade e aumentar precisão
                self.model_config["top_p"] = max(0.7, self.model_config["top_p"] - 0.1)
                self.model_config["frequency_penalty"] = min(1.0, self.model_config["frequency_penalty"] + 0.1)
            
            logger.info("✅ Otimização de parâmetros concluída")
            
        except Exception as e:
            logger.error(f"❌ Erro na otimização de parâmetros: {e}", exc_info=True)
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Obter status atual do modelo e agente"""
        try:
            status = {
                "agent_initialized": self.agent is not None,
                "agent_state": self.agent.state.value if self.agent else "unknown",
                "current_config": self.model_config.copy(),
                "performance_metrics": self.performance_metrics.copy(),
                "memory_size": len(self.agent.memory.messages) if self.agent else 0
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Erro ao obter status do modelo: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """Verificar saúde do serviço de IA"""
        try:
            if not self.agent:
                return False
            
            # Teste simples de funcionamento
            test_msg = AgentMessage(role="user", content="teste")
            self.agent.memory.messages = [test_msg]
            
            # Verificar se o agente responde
            return self.agent.state != AgentState.ERROR
            
        except Exception as e:
            logger.error(f"Erro no health check do AI Service: {e}")
            return False
    
    async def cleanup(self):
        """Limpar recursos do serviço"""
        try:
            if self.agent:
                await self.agent.cleanup()
                self.agent = None
            logger.info("🧹 Serviço de IA limpo")
        except Exception as e:
            logger.error(f"Erro no cleanup do AI Service: {e}", exc_info=True)