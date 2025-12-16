'use client'

import { useState, useEffect } from 'react'
import { Sparkles } from 'lucide-react'
import { Header } from '@/components/Header'
import { QueryForm } from '@/components/QueryForm'
import { AnswerDisplay } from '@/components/AnswerDisplay'
import { HistoryList } from '@/components/HistoryList'
import { QueryMode, QueryResponse, HistoryItem } from '@/lib/types'
import { submitQuery } from '@/lib/api'
import { saveQuery, getHistory, deleteHistoryItem } from '@/lib/storage'

export default function UserApp() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<QueryMode>('recall')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])

  // Load history and check for reload request
  useEffect(() => {
    setHistory(getHistory())

    // Check if we're loading a query from history
    const reloadData = sessionStorage.getItem('reload_query')
    if (reloadData) {
      sessionStorage.removeItem('reload_query')
      try {
        const item: HistoryItem = JSON.parse(reloadData)
        setQuery(item.query)
        setMode(item.mode)
        setResponse(item.response)
      } catch {
        // Ignore parse errors
      }
    }
  }, [])

  const handleSubmit = async () => {
    if (!query.trim()) return

    setLoading(true)
    setError(null)

    try {
      const data = await submitQuery(query, mode)
      setResponse(data)

      // Save to history
      saveQuery(query, mode, data)
      setHistory(getHistory())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed')
      setResponse(null)
    } finally {
      setLoading(false)
    }
  }

  const handleHistorySelect = (item: HistoryItem) => {
    setQuery(item.query)
    setMode(item.mode)
    setResponse(item.response)
    setError(null)
  }

  const handleHistoryDelete = (id: string) => {
    deleteHistoryItem(id)
    setHistory(getHistory())
  }

  return (
    <div className="min-h-screen animated-gradient">
      <Header />

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
          {/* Main Query Area */}
          <div className="lg:col-span-2 space-y-6 animate-fade-in">
            <QueryForm
              query={query}
              mode={mode}
              loading={loading}
              onQueryChange={setQuery}
              onModeChange={setMode}
              onSubmit={handleSubmit}
            />

            {/* Error Display */}
            {error && (
              <div className="glass rounded-2xl p-6 border-l-4 border-red-500 animate-slide-down">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-semibold text-red-900 dark:text-red-200">Error</h3>
                    <p className="text-red-800 dark:text-red-300 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Response Display */}
            {response && <AnswerDisplay response={response} />}

            {/* Empty State */}
            {!response && !error && !loading && (
              <div className="glass rounded-2xl p-12 text-center backdrop-blur-xl animate-scale-in">
                <div className="inline-block p-4 rounded-full bg-gradient-brand mb-6 animate-float">
                  <Sparkles className="w-12 h-12 text-white" />
                </div>
                <h3 className="text-3xl font-display font-bold mb-3 gradient-text">
                  Ask Your Organization
                </h3>
                <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
                  Query decisions, context, and insights from your organizational memory with evidence-backed answers.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left max-w-3xl mx-auto">
                  <div className="group p-6 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border border-blue-200 dark:border-blue-800 hover:shadow-glow transition-all duration-300 hover:-translate-y-1">
                    <div className="w-10 h-10 rounded-lg bg-blue-500 flex items-center justify-center mb-3">
                      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h4 className="font-display font-bold text-blue-900 dark:text-blue-200 mb-2">Recall</h4>
                    <p className="text-sm text-blue-700 dark:text-blue-400">Retrieve past decisions and organizational context</p>
                  </div>
                  <div className="group p-6 rounded-xl bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950/30 dark:to-pink-950/30 border border-purple-200 dark:border-purple-800 hover:shadow-glow transition-all duration-300 hover:-translate-y-1">
                    <div className="w-10 h-10 rounded-lg bg-purple-500 flex items-center justify-center mb-3">
                      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </div>
                    <h4 className="font-display font-bold text-purple-900 dark:text-purple-200 mb-2">Reflection</h4>
                    <p className="text-sm text-purple-700 dark:text-purple-400">Analyze patterns and discover insights</p>
                  </div>
                  <div className="group p-6 rounded-xl bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-950/30 dark:to-emerald-950/30 border border-green-200 dark:border-green-800 hover:shadow-glow transition-all duration-300 hover:-translate-y-1">
                    <div className="w-10 h-10 rounded-lg bg-green-500 flex items-center justify-center mb-3">
                      <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                      </svg>
                    </div>
                    <h4 className="font-display font-bold text-green-900 dark:text-green-200 mb-2">Projection</h4>
                    <p className="text-sm text-green-700 dark:text-green-400">Explore future scenarios and possibilities</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar - Recent History */}
          <div className="lg:col-span-1 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <div className="glass rounded-2xl p-6 sticky top-24 backdrop-blur-xl">
              <h3 className="font-display font-bold text-xl mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Recent Queries
              </h3>
              <HistoryList
                items={history.slice(0, 5)}
                onSelect={handleHistorySelect}
                onDelete={handleHistoryDelete}
                compact
              />
              {history.length > 5 && (
                <a
                  href="/history"
                  className="block mt-4 text-center text-sm font-medium text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-colors py-2 px-4 rounded-lg hover:bg-brand-50 dark:hover:bg-brand-950/30"
                >
                  View all {history.length} queries →
                </a>
              )}
              {history.length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No queries yet. Start by asking a question above.
                </p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
