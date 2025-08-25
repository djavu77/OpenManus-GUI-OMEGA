/**
 * Dashboard Administrativo
 * Sistema de IA Conversacional Avançada
 */

'use client';

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Users, 
  MessageSquare, 
  Brain, 
  Database,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Settings
} from 'lucide-react';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface AdminMetrics {
  conversations: {
    total: number;
    total_messages: number;
    unique_users: number;
  };
  feedback: {
    total: number;
    average_rating: number;
    positive_rate: number;
  };
  knowledge_base: {
    total_items: number;
    categories: number;
    avg_confidence: number;
    total_usage: number;
  };
  learning: {
    [key: string]: {
      total_sessions: number;
      completed_sessions: number;
      success_rate: number;
    };
  };
  system: {
    cpu: { percent: number };
    memory: { percent: number; total: number; used: number };
    disk: { percent: number; total: number; used: number };
  };
}

interface TrendData {
  response_time: Array<{ date: string; avg_response_time: number }>;
  user_satisfaction: Array<{ date: string; avg_rating: number; feedback_count: number }>;
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [trends, setTrends] = useState<TrendData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 30000); // Atualizar a cada 30 segundos
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      // Carregar métricas
      const metricsResponse = await fetch('/api/metrics');
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }

      // Carregar tendências
      const trendsResponse = await fetch('/api/admin/trends');
      if (trendsResponse.ok) {
        const trendsData = await trendsResponse.json();
        setTrends(trendsData);
      }

      setLoading(false);
    } catch (error) {
      console.error('Erro ao carregar dados do dashboard:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando dashboard...</p>
        </div>
      </div>
    );
  }

  const StatCard = ({ title, value, subtitle, icon: Icon, color = "blue" }: any) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
        <div className={`w-12 h-12 bg-${color}-100 rounded-lg flex items-center justify-center`}>
          <Icon className={`w-6 h-6 text-${color}-600`} />
        </div>
      </div>
    </motion.div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dashboard Administrativo</h1>
              <p className="text-gray-600">Sistema de IA Conversacional Avançada</p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-sm text-gray-600">Sistema Online</span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <nav className="flex space-x-8">
          {[
            { id: 'overview', label: 'Visão Geral', icon: BarChart3 },
            { id: 'learning', label: 'Aprendizado', icon: Brain },
            { id: 'knowledge', label: 'Base de Conhecimento', icon: Database },
            { id: 'system', label: 'Sistema', icon: Settings },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        {activeTab === 'overview' && metrics && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard
                title="Total de Conversas"
                value={metrics.conversations.total}
                subtitle={`${metrics.conversations.unique_users} usuários únicos`}
                icon={MessageSquare}
                color="blue"
              />
              <StatCard
                title="Rating Médio"
                value={`${metrics.feedback.average_rating.toFixed(1)}/5`}
                subtitle={`${metrics.feedback.positive_rate.toFixed(1)}% positivo`}
                icon={TrendingUp}
                color="green"
              />
              <StatCard
                title="Base de Conhecimento"
                value={metrics.knowledge_base.total_items}
                subtitle={`${metrics.knowledge_base.categories} categorias`}
                icon={Database}
                color="purple"
              />
              <StatCard
                title="CPU do Sistema"
                value={`${metrics.system.cpu.percent.toFixed(1)}%`}
                subtitle={`Memória: ${metrics.system.memory.percent.toFixed(1)}%`}
                icon={BarChart3}
                color="orange"
              />
            </div>

            {/* Charts */}
            {trends && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Response Time Trend */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Tempo de Resposta</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={trends.response_time}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Line 
                        type="monotone" 
                        dataKey="avg_response_time" 
                        stroke="#3b82f6" 
                        strokeWidth={2}
                        dot={{ fill: '#3b82f6' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* User Satisfaction Trend */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Satisfação do Usuário</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={trends.user_satisfaction}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis domain={[0, 5]} />
                      <Tooltip />
                      <Line 
                        type="monotone" 
                        dataKey="avg_rating" 
                        stroke="#10b981" 
                        strokeWidth={2}
                        dot={{ fill: '#10b981' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'learning' && metrics && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Sessões de Aprendizado</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(metrics.learning).map(([sessionType, data]) => (
                  <div key={sessionType} className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 capitalize mb-2">
                      {sessionType.replace('_', ' ')}
                    </h4>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Total:</span>
                        <span className="text-sm font-medium">{data.total_sessions}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Concluídas:</span>
                        <span className="text-sm font-medium">{data.completed_sessions}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Taxa de Sucesso:</span>
                        <span className="text-sm font-medium">{data.success_rate.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'knowledge' && metrics && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard
                title="Total de Itens"
                value={metrics.knowledge_base.total_items}
                icon={Database}
                color="purple"
              />
              <StatCard
                title="Categorias"
                value={metrics.knowledge_base.categories}
                icon={BarChart3}
                color="blue"
              />
              <StatCard
                title="Confiança Média"
                value={`${(metrics.knowledge_base.avg_confidence * 100).toFixed(1)}%`}
                icon={CheckCircle}
                color="green"
              />
              <StatCard
                title="Total de Usos"
                value={metrics.knowledge_base.total_usage}
                icon={TrendingUp}
                color="orange"
              />
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Gerenciar Base de Conhecimento</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors">
                  <Database className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-700">Adicionar Conhecimento</p>
                  <p className="text-xs text-gray-500">Importar documentos ou adicionar manualmente</p>
                </button>
                
                <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors">
                  <Brain className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-700">Treinar Modelo</p>
                  <p className="text-xs text-gray-500">Iniciar sessão de treinamento manual</p>
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'system' && metrics && (
          <div className="space-y-6">
            {/* System Resources */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">CPU</h3>
                  <div className={`w-3 h-3 rounded-full ${
                    metrics.system.cpu.percent < 70 ? 'bg-green-500' : 
                    metrics.system.cpu.percent < 90 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}></div>
                </div>
                <div className="text-3xl font-bold text-gray-900 mb-2">
                  {metrics.system.cpu.percent.toFixed(1)}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${metrics.system.cpu.percent}%` }}
                  ></div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Memória</h3>
                  <div className={`w-3 h-3 rounded-full ${
                    metrics.system.memory.percent < 70 ? 'bg-green-500' : 
                    metrics.system.memory.percent < 90 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}></div>
                </div>
                <div className="text-3xl font-bold text-gray-900 mb-2">
                  {metrics.system.memory.percent.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500 mb-2">
                  {(metrics.system.memory.used / 1024 / 1024 / 1024).toFixed(1)}GB / {(metrics.system.memory.total / 1024 / 1024 / 1024).toFixed(1)}GB
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-green-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${metrics.system.memory.percent}%` }}
                  ></div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Disco</h3>
                  <div className={`w-3 h-3 rounded-full ${
                    metrics.system.disk.percent < 70 ? 'bg-green-500' : 
                    metrics.system.disk.percent < 90 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}></div>
                </div>
                <div className="text-3xl font-bold text-gray-900 mb-2">
                  {metrics.system.disk.percent.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-500 mb-2">
                  {(metrics.system.disk.used / 1024 / 1024 / 1024).toFixed(1)}GB / {(metrics.system.disk.total / 1024 / 1024 / 1024).toFixed(1)}GB
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${metrics.system.disk.percent}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Service Status */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Status dos Serviços</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { name: 'OpenManus API', status: 'online', port: '8000' },
                  { name: 'PostgreSQL', status: 'online', port: '5432' },
                  { name: 'Redis', status: 'online', port: '6379' },
                  { name: 'ChromaDB', status: 'online', port: '8001' },
                  { name: 'Ollama', status: 'online', port: '11434' },
                  { name: 'Celery Worker', status: 'online', port: '-' },
                ].map((service) => (
                  <div key={service.name} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">{service.name}</p>
                      <p className="text-xs text-gray-500">Porta: {service.port}</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-xs text-green-600">Online</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}