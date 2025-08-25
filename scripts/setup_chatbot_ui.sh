#!/bin/bash

# Script de Configuração do ChatBot-UI
# Sistema de IA Conversacional Avançada

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

log_info "=== Configuração do Frontend ChatBot-UI ==="

# Verificar se Node.js está instalado
if ! command -v node >/dev/null 2>&1; then
    log_error "Node.js não encontrado. Execute install_prerequisites.sh primeiro"
    exit 1
fi

# Verificar se frontend já existe
if [[ -d "frontend" ]]; then
    log_success "Frontend já está configurado"
    exit 0
fi

# Criar estrutura do frontend
log_info "Criando estrutura do frontend..."
mkdir -p frontend/{chatbot-ui,admin-dashboard,components,hooks,utils}
mkdir -p config/frontend

# Clonar e configurar ChatBot-UI
log_info "Configurando ChatBot-UI..."
cd frontend

# Criar package.json para o projeto frontend
cat > package.json << 'EOF'
{
  "name": "sistema-ia-conversacional-frontend",
  "version": "1.0.0",
  "description": "Frontend para Sistema de IA Conversacional Avançada",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^14.0.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@types/node": "^20.10.5",
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "typescript": "^5.3.3",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "@headlessui/react": "^1.7.17",
    "@heroicons/react": "^2.0.18",
    "axios": "^1.6.2",
    "socket.io-client": "^4.7.4",
    "recharts": "^2.8.0",
    "react-hot-toast": "^2.4.1",
    "framer-motion": "^10.16.16",
    "lucide-react": "^0.294.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "react-syntax-highlighter": "^15.5.0"
  },
  "devDependencies": {
    "eslint": "^8.56.0",
    "eslint-config-next": "^14.0.4",
    "@tailwindcss/typography": "^0.5.10"
  }
}
EOF

# Instalar dependências
log_info "Instalando dependências do frontend..."
npm install

# Configurar Next.js
log_info "Configurando Next.js..."
cat > next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
EOF

# Configurar Tailwind CSS
log_info "Configurando Tailwind CSS..."
cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        secondary: {
          50: '#f8fafc',
          500: '#64748b',
          600: '#475569',
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
EOF

# Configurar PostCSS
cat > postcss.config.js << 'EOF'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

# Configurar TypeScript
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"],
      "@/components/*": ["./components/*"],
      "@/hooks/*": ["./hooks/*"],
      "@/utils/*": ["./utils/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
EOF

# Configurar variáveis de ambiente do frontend
log_info "Configurando variáveis de ambiente do frontend..."
cat > .env.local << 'EOF'
# Configuração do Frontend - Sistema IA Conversacional

# URL da API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Configurações da UI
NEXT_PUBLIC_APP_NAME=Sistema IA Conversacional
NEXT_PUBLIC_APP_VERSION=1.0.0

# Configurações de Desenvolvimento
NEXT_PUBLIC_DEBUG=true
EOF

cd ..

log_success "✅ Configuração do ChatBot-UI concluída!"
log_info "Próximo passo: Execute ./scripts/start_system.sh"