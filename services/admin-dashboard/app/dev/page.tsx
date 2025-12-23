'use client'

import { useState, useEffect } from 'react'
import {
    Terminal,
    Database,
    Play,
    RefreshCw,
    Trash2,
    Download,
    Code,
    Send,
    Copy,
    CheckCircle2,
    AlertCircle
} from 'lucide-react'
import { AdminNav } from '@/components/AdminNav'

export default function DevController() {
    const [activeTab, setActiveTab] = useState('api-test')
    const [apiEndpoint, setApiEndpoint] = useState('/v1/query')
    const [apiBody, setApiBody] = useState(`{
  "org_id": "00000000-0000-0000-0000-000000000000",
  "principal_id": "ad4e8240-683e-40a8-a00d-6d5c7c5bb32b",
  "mode": "recall",
  "query_text": "What decisions have we made about data storage?",
  "scopes": []
}`)
    const [apiResponse, setApiResponse] = useState('')
    const [apiLoading, setApiLoading] = useState(false)
    const [apiError, setApiError] = useState('')
    const [sqlQuery, setSqlQuery] = useState('')
    const [sqlResults, setSqlResults] = useState('')
    const [copied, setCopied] = useState(false)
    const [apiUrl, setApiUrl] = useState('http://localhost:8080')

    useEffect(() => {
        const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
        setApiUrl(url)
    }, [])

    const handleApiTest = async () => {
        setApiLoading(true)
        setApiError('')
        setApiResponse('')

        try {
            const url = `${apiUrl}${apiEndpoint}`
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                mode: 'cors',
                body: apiBody,
            })

            const data = await res.json()

            if (!res.ok) {
                throw new Error(data.detail || `HTTP error! status: ${res.status}`)
            }

            setApiResponse(JSON.stringify(data, null, 2))
        } catch (err: any) {
            setApiError(err.message)
            setApiResponse('')
        } finally {
            setApiLoading(false)
        }
    }

    const handleCopy = (text: string) => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    return (
        <div className="min-h-screen animated-gradient">
            <AdminNav />
            <div className="max-w-7xl mx-auto px-8 pb-8">
                {/* Header */}
                <div className="mb-8 animate-fade-in">
                    <h1 className="text-4xl font-display font-bold gradient-text mb-2">Developer Controller</h1>
                    <p className="text-gray-600">System testing and debugging tools</p>
                </div>

                {/* Tabs */}
                <div className="glass rounded-t-2xl p-2 flex gap-2 animate-slide-down">
                    <TabButton
                        active={activeTab === 'api-test'}
                        onClick={() => setActiveTab('api-test')}
                        icon={<Send className="w-4 h-4" />}
                    >
                        API Testing
                    </TabButton>
                    <TabButton
                        active={activeTab === 'database'}
                        onClick={() => setActiveTab('database')}
                        icon={<Database className="w-4 h-4" />}
                    >
                        Database
                    </TabButton>
                    <TabButton
                        active={activeTab === 'system'}
                        onClick={() => setActiveTab('system')}
                        icon={<Terminal className="w-4 h-4" />}
                    >
                        System
                    </TabButton>
                </div>

                {/* Content */}
                <div className="glass rounded-b-2xl rounded-tr-2xl p-8 animate-scale-in">
                    {activeTab === 'api-test' && (
                        <div className="space-y-6">
                            <h2 className="text-2xl font-display font-bold text-gray-900 mb-4">API Endpoint Testing</h2>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-2">Endpoint</label>
                                <input
                                    type="text"
                                    value={apiEndpoint}
                                    onChange={(e) => setApiEndpoint(e.target.value)}
                                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-all"
                                    placeholder="/v1/query"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-2">Request Body (JSON)</label>
                                <textarea
                                    value={apiBody}
                                    onChange={(e) => setApiBody(e.target.value)}
                                    rows={10}
                                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:border-brand-500 font-mono text-sm transition-all"
                                />
                            </div>

                            <button
                                onClick={handleApiTest}
                                disabled={apiLoading}
                                className="bg-gradient-brand text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 hover:shadow-glow-lg transition-all hover:scale-105 disabled:opacity-50"
                            >
                                <Play className="w-5 h-5" />
                                {apiLoading ? 'Sending...' : 'Send Request'}
                            </button>

                            {apiError && (
                                <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded-lg flex items-start gap-3">
                                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                                    <div>
                                        <h4 className="font-bold text-red-900">Error</h4>
                                        <p className="text-sm text-red-800">{apiError}</p>
                                    </div>
                                </div>
                            )}

                            {apiResponse && (
                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <label className="block text-sm font-bold text-gray-900">Response</label>
                                        <button
                                            onClick={() => handleCopy(apiResponse)}
                                            className="text-sm text-gray-600 hover:text-brand-600 flex items-center gap-1"
                                        >
                                            {copied ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                            {copied ? 'Copied!' : 'Copy'}
                                        </button>
                                    </div>
                                    <pre className="bg-gray-50 border-2 border-gray-200 rounded-xl p-4 overflow-auto max-h-96 text-sm font-mono">
                                        {apiResponse}
                                    </pre>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'database' && (
                        <div className="space-y-6">
                            <h2 className="text-2xl font-display font-bold text-gray-900 mb-4">Database Queries</h2>

                            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg mb-6">
                                <p className="text-sm text-yellow-800">
                                    <strong>Warning:</strong> Direct database access. Use with caution in production.
                                </p>
                            </div>

                            <div>
                                <label className="block text-sm font-bold text-gray-900 mb-2">SQL Query</label>
                                <textarea
                                    value={sqlQuery}
                                    onChange={(e) => setSqlQuery(e.target.value)}
                                    rows={6}
                                    placeholder="SELECT * FROM artifact LIMIT 10;"
                                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:border-brand-500 font-mono text-sm transition-all"
                                />
                            </div>

                            <div className="flex gap-3">
                                <button className="bg-gradient-brand text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 hover:shadow-glow-lg transition-all hover:scale-105">
                                    <Play className="w-5 h-5" />
                                    Execute Query
                                </button>
                                <button className="bg-gray-100 text-gray-700 px-6 py-3 rounded-xl font-bold flex items-center gap-2 hover:bg-gray-200 transition-all">
                                    <Download className="w-5 h-5" />
                                    Export Results
                                </button>
                            </div>

                            {/* Quick Queries */}
                            <div className="mt-8">
                                <h3 className="text-lg font-bold text-gray-900 mb-3">Quick Queries</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <QuickQuery
                                        title="Count Artifacts"
                                        query="SELECT COUNT(*) FROM artifact;"
                                        onClick={setSqlQuery}
                                    />
                                    <QuickQuery
                                        title="Recent Events"
                                        query="SELECT * FROM event_log ORDER BY occurred_at DESC LIMIT 10;"
                                        onClick={setSqlQuery}
                                    />
                                    <QuickQuery
                                        title="Evidence Spans"
                                        query="SELECT * FROM evidence_span LIMIT 20;"
                                        onClick={setSqlQuery}
                                    />
                                    <QuickQuery
                                        title="User Stats"
                                        query="SELECT actor_principal_id, COUNT(*) as event_count FROM event_log GROUP BY actor_principal_id;"
                                        onClick={setSqlQuery}
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'system' && (
                        <div className="space-y-6">
                            <h2 className="text-2xl font-display font-bold text-gray-900 mb-4">System Controls</h2>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                <SystemAction
                                    icon={<RefreshCw className="w-6 h-6" />}
                                    title="Restart Services"
                                    description="Restart all Docker containers"
                                    buttonText="Restart"
                                    buttonClass="bg-blue-500 hover:bg-blue-600"
                                />
                                <SystemAction
                                    icon={<Trash2 className="w-6 h-6" />}
                                    title="Clear Cache"
                                    description="Clear all application caches"
                                    buttonText="Clear"
                                    buttonClass="bg-orange-500 hover:bg-orange-600"
                                />
                                <SystemAction
                                    icon={<Database className="w-6 h-6" />}
                                    title="Backup Database"
                                    description="Create database backup"
                                    buttonText="Backup"
                                    buttonClass="bg-green-500 hover:bg-green-600"
                                />
                                <SystemAction
                                    icon={<Download className="w-6 h-6" />}
                                    title="Export Logs"
                                    description="Download system logs"
                                    buttonText="Export"
                                    buttonClass="bg-purple-500 hover:bg-purple-600"
                                />
                                <SystemAction
                                    icon={<Terminal className="w-6 h-6" />}
                                    title="Run Migrations"
                                    description="Execute database migrations"
                                    buttonText="Migrate"
                                    buttonClass="bg-gray-600 hover:bg-gray-700"
                                />
                                <SystemAction
                                    icon={<Code className="w-6 h-6" />}
                                    title="Seed Data"
                                    description="Load sample data"
                                    buttonText="Seed"
                                    buttonClass="bg-indigo-500 hover:bg-indigo-600"
                                />
                            </div>

                            {/* Environment Info */}
                            <div className="mt-8">
                                <h3 className="text-lg font-bold text-gray-900 mb-3">Environment</h3>
                                <div className="glass-strong p-4 rounded-xl space-y-2 font-mono text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">API Gateway:</span>
                                        <span className="font-semibold">http://localhost:8080</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">User App:</span>
                                        <span className="font-semibold">http://localhost:3002</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Admin Dashboard:</span>
                                        <span className="font-semibold">http://localhost:3001</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Database:</span>
                                        <span className="font-semibold">postgres://localhost:5433</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

function TabButton({
    active,
    onClick,
    icon,
    children
}: {
    active: boolean
    onClick: () => void
    icon: React.ReactNode
    children: React.ReactNode
}) {
    return (
        <button
            onClick={onClick}
            className={`
        px-4 py-2.5 rounded-xl font-semibold transition-all flex items-center gap-2
        ${active
                    ? 'bg-gradient-brand text-white shadow-glow'
                    : 'text-gray-700 hover:bg-white/50'
                }
      `}
        >
            {icon}
            {children}
        </button>
    )
}

function QuickQuery({
    title,
    query,
    onClick
}: {
    title: string
    query: string
    onClick: (query: string) => void
}) {
    return (
        <button
            onClick={() => onClick(query)}
            className="glass-strong p-4 rounded-xl text-left hover:shadow-glow transition-all hover:-translate-y-1"
        >
            <h4 className="font-bold text-gray-900 mb-1">{title}</h4>
            <code className="text-xs text-gray-600 block truncate">{query}</code>
        </button>
    )
}

function SystemAction({
    icon,
    title,
    description,
    buttonText,
    buttonClass
}: {
    icon: React.ReactNode
    title: string
    description: string
    buttonText: string
    buttonClass: string
}) {
    return (
        <div className="glass p-5 rounded-xl">
            <div className="text-brand-600 mb-3">
                {icon}
            </div>
            <h4 className="font-bold text-gray-900 mb-1">{title}</h4>
            <p className="text-sm text-gray-600 mb-4">{description}</p>
            <button className={`${buttonClass} text-white px-4 py-2 rounded-lg text-sm font-semibold w-full transition-all hover:scale-105`}>
                {buttonText}
            </button>
        </div>
    )
}
