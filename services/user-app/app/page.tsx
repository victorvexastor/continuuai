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
