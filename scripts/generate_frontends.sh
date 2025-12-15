#!/usr/bin/env bash
set -euo pipefail

# ContinuuAI Frontend Generator
# Generates all required files for user-app and admin-dashboard

echo "🎨 Generating ContinuuAI Frontend Applications..."

# ============================================
# USER APP - Configuration Files
# ============================================

cat > services/user-app/tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
EOF

cat > services/user-app/tailwind.config.js << 'EOF'
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
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
}
EOF

cat > services/user-app/postcss.config.js << 'EOF'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

# ============================================
# USER APP - Core Application Files
# ============================================

cat > services/user-app/app/globals.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground-rgb: 255, 255, 255;
    --background-start-rgb: 0, 0, 0;
    --background-end-rgb: 0, 0, 0;
  }
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
EOF

cat > services/user-app/app/layout.tsx << 'EOF'
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ContinuuAI - Organizational Memory',
  description: 'Evidence-based decision intelligence for your organization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
EOF

cat > services/user-app/app/page.tsx << 'EOF'
'use client'

import { useState } from 'react'
import { Search, History, Settings, Sparkles } from 'lucide-react'

type QueryMode = 'recall' | 'reflection' | 'projection'

interface Evidence {
  evidence_span_id: string
  artifact_id: string
  quote: string
  confidence: number
}

interface QueryResponse {
  contract_version: string
  mode: string
  answer: string
  evidence: Evidence[]
  policy: {
    status: string
    notes: string[]
  }
}

export default function UserApp() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<QueryMode>('recall')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
      const res = await fetch(`${apiUrl}/v1/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: '00000000-0000-0000-0000-000000000000',
          principal_id: '00000000-0000-0000-0000-000000000001',
          mode,
          query_text: query,
          scopes: []
        })
      })

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`)
      }

      const data = await res.json()
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Sparkles className="w-8 h-8 text-brand-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">ContinuuAI</h1>
              <p className="text-sm text-gray-600">Organizational Memory</p>
            </div>
          </div>
          <nav className="flex items-center space-x-4">
            <button className="p-2 hover:bg-gray-100 rounded-lg transition">
              <History className="w-5 h-5 text-gray-600" />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition">
              <Settings className="w-5 h-5 text-gray-600" />
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Query Form */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Query Mode
              </label>
              <div className="flex space-x-2">
                {(['recall', 'reflection', 'projection'] as QueryMode[]).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={`px-4 py-2 rounded-lg font-medium transition ${
                      mode === m
                        ? 'bg-brand-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {m.charAt(0).toUpperCase() + m.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label htmlFor="query" className="block text-sm font-semibold text-gray-700 mb-2">
                Your Question
              </label>
              <textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={4}
                placeholder="What do you want to know? Ask about decisions, context, or future scenarios..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="w-full bg-brand-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                  <span>Searching memory...</span>
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  <span>Search Memory</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800 font-medium">Error: {error}</p>
          </div>
        )}

        {/* Response Display */}
        {response && (
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="mb-4">
              <span className="inline-block px-3 py-1 bg-brand-100 text-brand-800 rounded-full text-sm font-semibold">
                {response.mode} mode
              </span>
            </div>

            <div className="mb-6">
              <h2 className="text-xl font-bold text-gray-900 mb-3">Answer</h2>
              <p className="text-gray-700 leading-relaxed">{response.answer}</p>
            </div>

            {response.evidence.length > 0 && (
              <div>
                <h3 className="text-lg font-bold text-gray-900 mb-3">
                  Evidence ({response.evidence.length} sources)
                </h3>
                <div className="space-y-3">
                  {response.evidence.map((ev, idx) => (
                    <div key={idx} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-xs font-semibold text-gray-500">Source {idx + 1}</span>
                        <span className="text-xs font-semibold text-brand-600">
                          {Math.round(ev.confidence * 100)}% confidence
                        </span>
                      </div>
                      <blockquote className="text-sm text-gray-700 italic border-l-4 border-brand-400 pl-3">
                        "{ev.quote}"
                      </blockquote>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-6 pt-6 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                Policy: {response.policy.status} • Contract: {response.contract_version}
              </p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!response && !error && !loading && (
          <div className="bg-white rounded-xl shadow-lg p-12 text-center">
            <Sparkles className="w-16 h-16 text-brand-400 mx-auto mb-4" />
            <h3 className="text-2xl font-bold text-gray-900 mb-2">Ask Your Organization</h3>
            <p className="text-gray-600 mb-6">
              Query decisions, context, and insights from your organizational memory.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left max-w-2xl mx-auto">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-1">Recall</h4>
                <p className="text-sm text-blue-700">Retrieve past decisions and context</p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <h4 className="font-semibold text-purple-900 mb-1">Reflection</h4>
                <p className="text-sm text-purple-700">Analyze patterns and insights</p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <h4 className="font-semibold text-green-900 mb-1">Projection</h4>
                <p className="text-sm text-green-700">Explore future scenarios</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
EOF

cat > services/user-app/Dockerfile << 'EOF'
FROM node:20-alpine AS base

# Dependencies
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Builder
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Runner
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
EOF

echo "✅ User App files generated"

# ============================================
# ADMIN DASHBOARD - Configuration + Files
# ============================================

cat > services/admin-dashboard/tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
EOF

cat > services/admin-dashboard/tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

cat > services/admin-dashboard/postcss.config.js << 'EOF'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

cat > services/admin-dashboard/app/globals.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

cat > services/admin-dashboard/app/layout.tsx << 'EOF'
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ContinuuAI Admin Dashboard',
  description: 'System management and monitoring',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50">{children}</body>
    </html>
  )
}
EOF

# Admin dashboard page already exists, update it with enhanced version
cat > services/admin-dashboard/app/page.tsx << 'EOF'
'use client'

import { useEffect, useState } from 'react'
import { Activity, Database, Server, Zap, AlertCircle, CheckCircle2 } from 'lucide-react'

interface HealthStatus {
  postgres: boolean
  api: boolean
  retrieval: boolean
  loading: boolean
}

interface Event {
  event_id: string
  event_type: string
  occurred_at: string
  actor_principal_id: string
}

export default function AdminDashboard() {
  const [health, setHealth] = useState<HealthStatus>({
    postgres: false,
    api: false,
    retrieval: false,
    loading: true,
  })
  const [events, setEvents] = useState<Event[]>([])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
        const apiRes = await fetch(`${apiUrl}/healthz`)
        const apiHealthy = apiRes.ok

        const retrievalRes = await fetch('http://localhost:8081/v1/health')
        const retrievalHealthy = retrievalRes.ok

        setHealth({
          api: apiHealthy,
          retrieval: retrievalHealthy,
          postgres: apiHealthy,
          loading: false,
        })
      } catch (err) {
        setHealth({ postgres: false, api: false, retrieval: false, loading: false })
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
          <p className="text-gray-600">ContinuuAI System Management</p>
        </div>

        {/* System Health Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <HealthCard
            icon={<Database className="w-8 h-8" />}
            title="PostgreSQL"
            healthy={health.postgres}
            loading={health.loading}
          />
          <HealthCard
            icon={<Server className="w-8 h-8" />}
            title="API Gateway"
            healthy={health.api}
            loading={health.loading}
          />
          <HealthCard
            icon={<Zap className="w-8 h-8" />}
            title="Retrieval Service"
            healthy={health.retrieval}
            loading={health.loading}
          />
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4 flex items-center">
            <Activity className="w-6 h-6 mr-2 text-blue-600" />
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <ActionButton title="View Logs" command="make logs" />
            <ActionButton title="Run Tests" command="make test" />
            <ActionButton title="Backup DB" command="make backup" />
            <ActionButton title="System Status" command="make status" />
          </div>
        </div>

        {/* Info Banner */}
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
          <div className="flex">
            <div className="flex-shrink-0">
              <CheckCircle2 className="h-5 w-5 text-blue-400" />
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>Phase 1 Complete:</strong> Backend services operational. 
                Expand this dashboard with user management, event log viewer, and ACL management as needed.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function HealthCard({ 
  icon, 
  title, 
  healthy, 
  loading 
}: { 
  icon: React.ReactNode
  title: string
  healthy: boolean
  loading: boolean
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`${healthy ? 'text-green-600' : 'text-red-600'}`}>
          {icon}
        </div>
        {loading ? (
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-400" />
        ) : healthy ? (
          <CheckCircle2 className="w-6 h-6 text-green-600" />
        ) : (
          <AlertCircle className="w-6 h-6 text-red-600" />
        )}
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
      <p className={`text-sm font-medium ${healthy ? 'text-green-600' : 'text-red-600'}`}>
        {loading ? 'Checking...' : healthy ? 'Healthy' : 'Down'}
      </p>
    </div>
  )
}

function ActionButton({ title, command }: { title: string; command: string }) {
  return (
    <button className="bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg p-4 text-left transition">
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      <code className="text-xs text-gray-600 bg-gray-200 px-2 py-1 rounded">{command}</code>
    </button>
  )
}
EOF

cat > services/admin-dashboard/Dockerfile << 'EOF'
FROM node:20-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
EOF

echo "✅ Admin Dashboard files generated"
echo ""
echo "✅ All frontend files generated successfully!"
echo ""
echo "Next steps:"
echo "  1. cd services/user-app && npm install"
echo "  2. cd services/admin-dashboard && npm install"
echo "  3. Update docker-compose.yml to enable frontend services"
