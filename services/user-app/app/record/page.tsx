'use client'

import { useState, useEffect } from 'react'
import { Header } from '@/components/Header'
import { RecordDecision } from '@/components/RecordDecision'

interface DecisionStream {
  id: string
  name: string
}

export default function RecordPage() {
  const [streams, setStreams] = useState<DecisionStream[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/decisions')
      .then(res => res.json())
      .then(data => {
        if (data.streams) {
          setStreams(data.streams)
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleSubmitDecision = async (decision: any) => {
    // TODO: Call API endpoint POST /v1/decisions
    const response = await fetch('/api/decisions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision)
    })

    if (!response.ok) {
      throw new Error(await response.text())
    }

    return response.json()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <p className="text-gray-600">Loading...</p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Header />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <RecordDecision onSubmit={handleSubmitDecision} streams={streams} />
      </main>
    </div>
  )
}
