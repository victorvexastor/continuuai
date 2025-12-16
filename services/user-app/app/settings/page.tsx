'use client'

import { useState, useEffect } from 'react'
import { Server, Trash2, CheckCircle2, XCircle, RefreshCw } from 'lucide-react'
import { Header } from '@/components/Header'
import { getApiUrl, checkHealth } from '@/lib/api'
import { clearHistory, getHistory } from '@/lib/storage'

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState('')
  const [apiHealthy, setApiHealthy] = useState<boolean | null>(null)
  const [checkingHealth, setCheckingHealth] = useState(false)
  const [historyCount, setHistoryCount] = useState(0)
  const [showConfirmClear, setShowConfirmClear] = useState(false)
  const [cleared, setCleared] = useState(false)

  useEffect(() => {
    setApiUrl(getApiUrl())
    setHistoryCount(getHistory().length)
    handleCheckHealth()
  }, [])

  const handleCheckHealth = async () => {
    setCheckingHealth(true)
    const healthy = await checkHealth()
    setApiHealthy(healthy)
    setCheckingHealth(false)
  }

  const handleClearHistory = () => {
    clearHistory()
    setHistoryCount(0)
    setShowConfirmClear(false)
    setCleared(true)
    setTimeout(() => setCleared(false), 3000)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Header />
      
      <main className="max-w-2xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Settings</h2>

        {/* API Configuration */}
        <section className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <Server className="w-6 h-6 text-brand-600" />
            <h3 className="text-lg font-semibold text-gray-900">API Configuration</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Endpoint
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={apiUrl}
                  readOnly
                  className="flex-1 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-700 font-mono text-sm"
                />
                <button
                  onClick={handleCheckHealth}
                  disabled={checkingHealth}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition flex items-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${checkingHealth ? 'animate-spin' : ''}`} />
                  Check
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Set via NEXT_PUBLIC_API_URL environment variable
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Status:</span>
              {apiHealthy === null ? (
                <span className="text-gray-400">Unknown</span>
              ) : apiHealthy ? (
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle2 className="w-4 h-4" />
                  Connected
                </span>
              ) : (
                <span className="flex items-center gap-1 text-red-600">
                  <XCircle className="w-4 h-4" />
                  Unreachable
                </span>
              )}
            </div>
          </div>
        </section>

        {/* Data Management */}
        <section className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <Trash2 className="w-6 h-6 text-brand-600" />
            <h3 className="text-lg font-semibold text-gray-900">Data Management</h3>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium text-gray-900">Query History</p>
                <p className="text-sm text-gray-500">
                  {historyCount} saved quer{historyCount !== 1 ? 'ies' : 'y'} stored locally
                </p>
              </div>
              <button
                onClick={() => setShowConfirmClear(true)}
                disabled={historyCount === 0}
                className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Clear
              </button>
            </div>

            {cleared && (
              <div className="p-3 bg-green-50 text-green-800 rounded-lg text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                History cleared successfully
              </div>
            )}
          </div>
        </section>

        {/* About */}
        <section className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">About</h3>
          <div className="space-y-2 text-sm text-gray-600">
            <p><strong>ContinuuAI User App</strong></p>
            <p>Evidence-based decision intelligence for your organization.</p>
            <p className="text-xs text-gray-400 mt-4">
              Version 1.0.0 • Built with Next.js 15
            </p>
          </div>
        </section>

        {/* Confirm Clear Modal */}
        {showConfirmClear && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 max-w-sm mx-4">
              <h3 className="text-lg font-bold text-gray-900 mb-2">Clear History?</h3>
              <p className="text-gray-600 mb-4">
                This will permanently delete all {historyCount} saved queries. This cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowConfirmClear(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleClearHistory}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
