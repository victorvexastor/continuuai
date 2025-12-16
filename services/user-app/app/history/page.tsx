'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Trash2, ArrowLeft } from 'lucide-react'
import { Header } from '@/components/Header'
import { HistoryList } from '@/components/HistoryList'
import { AnswerDisplay } from '@/components/AnswerDisplay'
import { HistoryItem } from '@/lib/types'
import { getHistory, deleteHistoryItem, clearHistory } from '@/lib/storage'

export default function HistoryPage() {
  const router = useRouter()
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null)
  const [showConfirmClear, setShowConfirmClear] = useState(false)

  useEffect(() => {
    setHistory(getHistory())
  }, [])

  const handleSelect = (item: HistoryItem) => {
    setSelectedItem(item)
  }

  const handleDelete = (id: string) => {
    deleteHistoryItem(id)
    setHistory(getHistory())
    if (selectedItem?.id === id) {
      setSelectedItem(null)
    }
  }

  const handleClearAll = () => {
    clearHistory()
    setHistory([])
    setSelectedItem(null)
    setShowConfirmClear(false)
  }

  const handleLoadQuery = (item: HistoryItem) => {
    // Store the item to reload and navigate to home
    sessionStorage.setItem('reload_query', JSON.stringify(item))
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Header />
      
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Query History</h2>
            <p className="text-gray-600">
              {history.length} saved quer{history.length !== 1 ? 'ies' : 'y'}
            </p>
          </div>
          
          {history.length > 0 && (
            <button
              onClick={() => setShowConfirmClear(true)}
              className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition"
            >
              <Trash2 className="w-4 h-4" />
              Clear All
            </button>
          )}
        </div>

        {/* Confirm Clear Modal */}
        {showConfirmClear && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 max-w-sm mx-4">
              <h3 className="text-lg font-bold text-gray-900 mb-2">Clear All History?</h3>
              <p className="text-gray-600 mb-4">
                This will permanently delete all {history.length} saved queries. This cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowConfirmClear(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleClearAll}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                >
                  Clear All
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* History List */}
          <div className="bg-white rounded-xl shadow-lg p-4">
            <HistoryList
              items={history}
              onSelect={handleSelect}
              onDelete={handleDelete}
            />
          </div>

          {/* Selected Item Detail */}
          <div>
            {selectedItem ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-700">Query Details</h3>
                  <button
                    onClick={() => handleLoadQuery(selectedItem)}
                    className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition text-sm font-medium"
                  >
                    Load This Query
                  </button>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-500 mb-1">Original Query</p>
                  <p className="text-gray-800">{selectedItem.query}</p>
                </div>
                
                <AnswerDisplay response={selectedItem.response} />
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-lg p-12 text-center">
                <ArrowLeft className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">Select a query to view details</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
