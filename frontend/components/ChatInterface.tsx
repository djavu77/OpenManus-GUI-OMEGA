/**
 * Interface de Chat Avançada
 * Componente principal para interação com IA
 */

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Bot, User, ThumbsUp, ThumbsDown, Copy, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  rating?: number;
  metadata?: {
    response_time?: number;
    tokens_used?: number;
    model_version?: string;
  };
}

interface ChatInterfaceProps {
  onFeedback?: (messageId: string, rating: number, comment?: string) => void;
  onMetricsUpdate?: (metrics: any) => void;
  className?: string;
}

export default function ChatInterface({ 
  onFeedback, 
  onMetricsUpdate, 
  className = '' 
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll para última mensagem
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Ajustar altura do textarea automaticamente
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [inputValue]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setIsTyping(true);

    const startTime = Date.now();

    try {
      const response = await fetch('/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'openmanus-tinyllama',
          messages: [
            ...messages.map(msg => ({
              role: msg.role,
              content: msg.content
            })),
            { role: 'user', content: userMessage.content }
          ],
          stream: true,
          temperature: 0.7,
          max_tokens: 2048
        }),
      });

      if (!response.ok) {
        throw new Error(`Erro na API: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Não foi possível ler a resposta');

      let assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        metadata: {
          response_time: 0,
          model_version: 'tinyllama-v1'
        }
      };

      setMessages(prev => [...prev, assistantMessage]);
      setIsTyping(false);

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              const content = parsed.choices?.[0]?.delta?.content;
              
              if (content) {
                assistantMessage.content += content;
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantMessage.id 
                      ? { 
                          ...msg, 
                          content: assistantMessage.content,
                          metadata: {
                            ...msg.metadata,
                            response_time: Date.now() - startTime
                          }
                        }
                      : msg
                  )
                );
              }
            } catch (e) {
              // Ignorar erros de parsing de chunks individuais
            }
          }
        }
      }

      // Atualizar métricas
      if (onMetricsUpdate) {
        onMetricsUpdate({
          response_time: Date.now() - startTime,
          message_length: assistantMessage.content.length
        });
      }

    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      
      // Adicionar mensagem de erro
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const rateMessage = async (messageId: string, rating: number) => {
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message_id: messageId,
          rating: rating,
          feedback_type: 'rating'
        }),
      });

      if (response.ok) {
        setMessages(prev =>
          prev.map(msg =>
            msg.id === messageId ? { ...msg, rating } : msg
          )
        );
        
        if (onFeedback) {
          onFeedback(messageId, rating);
        }
      }
    } catch (error) {
      console.error('Erro ao enviar feedback:', error);
    }
  };

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
    // TODO: Adicionar toast de confirmação
  };

  const regenerateResponse = async (messageIndex: number) => {
    // TODO: Implementar regeneração de resposta
    console.log('Regenerando resposta para mensagem:', messageIndex);
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        <AnimatePresence>
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-12"
            >
              <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Bot className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                Bem-vindo ao Sistema IA Conversacional
              </h2>
              <p className="text-gray-600 max-w-md mx-auto leading-relaxed">
                Sou um assistente IA avançado com capacidades de aprendizado contínuo. 
                Posso ajudar com diversas tarefas e melhorar com base no seu feedback.
              </p>
              <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h3 className="font-semibold text-blue-900 mb-2">🧠 Auto-Aprendizado</h3>
                  <p className="text-sm text-blue-700">Aprendo com cada interação e feedback</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <h3 className="font-semibold text-green-900 mb-2">💾 Memória Persistente</h3>
                  <p className="text-sm text-green-700">Lembro de conversas anteriores</p>
                </div>
                <div className="p-4 bg-purple-50 rounded-lg">
                  <h3 className="font-semibold text-purple-900 mb-2">🚀 Evolução Contínua</h3>
                  <p className="text-sm text-purple-700">Melhoro constantemente</p>
                </div>
              </div>
            </motion.div>
          ) : (
            messages.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex max-w-[85%] ${
                  message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                } items-start space-x-3`}>
                  {/* Avatar */}
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.role === 'user' 
                      ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white' 
                      : 'bg-gradient-to-r from-gray-200 to-gray-300 text-gray-700'
                  }`}>
                    {message.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                  </div>
                  
                  {/* Message Bubble */}
                  <div className={`rounded-2xl px-5 py-4 ${
                    message.role === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white'
                      : 'bg-white text-gray-900 shadow-soft border border-gray-100'
                  }`}>
                    {/* Content */}
                    <div className="prose prose-sm max-w-none">
                      {message.role === 'assistant' ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            code({ node, inline, className, children, ...props }) {
                              const match = /language-(\w+)/.exec(className || '');
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  style={tomorrow}
                                  language={match[1]}
                                  PreTag="div"
                                  className="rounded-lg"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              );
                            }
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      ) : (
                        <div className="whitespace-pre-wrap">{message.content}</div>
                      )}
                    </div>
                    
                    {/* Message Actions */}
                    {message.role === 'assistant' && (
                      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
                        {/* Feedback Buttons */}
                        <div className="flex items-center space-x-3">
                          <span className="text-xs text-gray-500">Esta resposta foi útil?</span>
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={() => rateMessage(message.id, 5)}
                              className={`p-1.5 rounded-lg transition-all duration-200 ${
                                message.rating === 5
                                  ? 'text-green-600 bg-green-100 shadow-sm'
                                  : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                              }`}
                              title="Resposta útil"
                            >
                              <ThumbsUp className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => rateMessage(message.id, 1)}
                              className={`p-1.5 rounded-lg transition-all duration-200 ${
                                message.rating === 1
                                  ? 'text-red-600 bg-red-100 shadow-sm'
                                  : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                              }`}
                              title="Resposta não útil"
                            >
                              <ThumbsDown className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        
                        {/* Action Buttons */}
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => copyMessage(message.content)}
                            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
                            title="Copiar resposta"
                          >
                            <Copy className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => regenerateResponse(index)}
                            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
                            title="Regenerar resposta"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}
                    
                    {/* Metadata */}
                    {message.metadata && (
                      <div className="mt-2 text-xs text-gray-400 flex items-center space-x-3">
                        {message.metadata.response_time && (
                          <span>⏱️ {(message.metadata.response_time / 1000).toFixed(1)}s</span>
                        )}
                        {message.metadata.tokens_used && (
                          <span>🔤 {message.metadata.tokens_used} tokens</span>
                        )}
                        <span>🕒 {message.timestamp.toLocaleTimeString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
        
        {/* Typing Indicator */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex justify-start"
          >
            <div className="flex items-start space-x-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-gray-200 to-gray-300 flex items-center justify-center">
                <Bot className="w-5 h-5 text-gray-700" />
              </div>
              <div className="bg-white rounded-2xl px-5 py-4 shadow-soft border border-gray-100">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-4 pb-6">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-4">
          <div className="flex items-end space-x-4">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Digite sua mensagem aqui... (Shift + Enter para nova linha)"
                className="w-full resize-none border-0 focus:ring-0 focus:outline-none text-gray-900 placeholder-gray-500 bg-transparent"
                rows={1}
                maxLength={4000}
                disabled={isLoading}
                style={{ minHeight: '24px', maxHeight: '120px' }}
              />
              
              {/* Input Footer */}
              <div className="flex justify-between items-center mt-3 pt-3 border-t border-gray-100">
                <div className="flex items-center space-x-4 text-xs text-gray-400">
                  <span>{inputValue.length}/4000 caracteres</span>
                  <span>💡 Dica: Seja específico para melhores respostas</span>
                </div>
                
                <div className="flex items-center space-x-2">
                  {isLoading && (
                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                      <span>Processando...</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Send Button */}
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className={`rounded-xl p-3 transition-all duration-200 flex items-center justify-center ${
                !inputValue.trim() || isLoading
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
              }`}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}