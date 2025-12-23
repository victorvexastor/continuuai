'use client'

import { useState, useEffect, use } from 'react'
import Link from 'next/link'
import { Header } from '@/components/Header'
import { 
  ArrowLeft,
  Clock, 
  MessageSquare, 
  AlertCircle,
  CheckCircle,
  XCircle,
  User,
  Calendar,
  GitBranch,
  HelpCircle
} from 'lucide-react'

interface Alternative {
  option: string
  why_rejected: string
}

interface Dissent {
  id: string
  person: string
  concern: string
  reasoning: string
  status: 'open' | 'resolved' | 'acknowledged'
  resolution: string | null
}

interface Uncertainty {
  id: string
  aspect: string
  description: string
  impact_if_wrong: string
  mitigation: string
  status: 'open' | 'resolved'
  resolution: string | null
}

interface Outcome {
  id: string
  description: string
  outcome_type: 'positive' | 'negative' | 'mixed' | 'neutral'
  recorded_at: string
}

interface DecisionStream {
  id: string
  name: string
  color: string
}

interface DecisionBy {
  id: string
  name: string
}

interface DecisionDetail {
  id: string
  title: string
  what_decided: string
  reasoning: string
  constraints: string[]
  alternatives: Alternative[]
  decided_at: string
  status: 'active' | 'superseded' | 'reversed' | 'implemented'
  revisit_date: string | null
  stream: DecisionStream
  decided_by: DecisionBy
  dissent: Dissent[]
  uncertainty: Uncertainty[]
  outcomes: Outcome[]
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'active':
      return <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">Active</span>
    case 'superseded':
      return <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-medium">Superseded</span>
    case 'reversed':
      return <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">Reversed</span>
    case 'implemented':
      return <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">Implemented</span>
    default:
      return null
  }
}

function getDissentStatusIcon(status: string) {
  switch (status) {
    case 'resolved':
      return <CheckCircle className="w-5 h-5 text-green-500" />
    case 'acknowledged':
      return <AlertCircle className="w-5 h-5 text-amber-500" />
    default:
      return <XCircle className="w-5 h-5 text-red-500" />
  }
}

export default function DecisionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params)
  const [decision, setDecision] = useState<DecisionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/decisions/${resolvedParams.id}`)
      .then(res => {
        if (!res.ok) throw new Error('Decision not found')
        return res.json()
      })
      .then(data => {
        if (data.error) {
          setError(data.error)
        } else {
          setDecision(data)
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [resolvedParams.id])

  if (loading) {
    return (
      <div className="min-h-screen animated-gradient">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-2/3"></div>
            <div className="h-4 bg-gray-200 rounded w-1/3"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </main>
      </div>
    )
  }

  if (error || !decision) {
    return (
      <div className="min-h-screen animated-gradient">
        <Header />
        <main className="max-w-4xl mx-auto px-4 py-8">
          <Link href="/dashboard" className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6">
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-xl p-6">
            <p className="text-red-800">{error || 'Decision not found'}</p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen animated-gradient">
      <Header />
      
      <main className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Back Link */}
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        {/* Header */}
        <div className="glass rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <span
                className="inline-block w-3 h-3 rounded-full"
                style={{ backgroundColor: decision.stream.color }}
              />
              <span className="text-sm font-medium text-gray-600">{decision.stream.name}</span>
            </div>
            {getStatusBadge(decision.status)}
          </div>
          
          <h1 className="text-2xl font-display font-bold text-gray-900 mb-4">
            {decision.title}
          </h1>
          
          <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <User className="w-4 h-4" />
              <span>{decision.decided_by.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <span>{formatDate(decision.decided_at)}</span>
            </div>
            {decision.revisit_date && (
              <div className="flex items-center gap-2 text-amber-600">
                <Clock className="w-4 h-4" />
                <span>Revisit: {formatDate(decision.revisit_date)}</span>
              </div>
            )}
          </div>
        </div>

        {/* What was decided */}
        <div className="glass rounded-xl p-6 mb-6">
          <h2 className="text-lg font-display font-bold mb-3">What was decided</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{decision.what_decided}</p>
        </div>

        {/* Reasoning */}
        <div className="glass rounded-xl p-6 mb-6">
          <h2 className="text-lg font-display font-bold mb-3">Reasoning & Context</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{decision.reasoning}</p>
          
          {decision.constraints.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h3 className="text-sm font-semibold text-gray-600 mb-2">Constraints</h3>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                {decision.constraints.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Alternatives Considered */}
        {decision.alternatives.length > 0 && (
          <div className="glass rounded-xl p-6 mb-6">
            <h2 className="text-lg font-display font-bold mb-3 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-gray-500" />
              Alternatives Considered
            </h2>
            <div className="space-y-3">
              {decision.alternatives.map((alt, i) => (
                <div key={i} className="p-4 bg-gray-50 rounded-lg">
                  <p className="font-semibold text-gray-900">{alt.option}</p>
                  <p className="text-sm text-gray-600 mt-1">
                    <span className="font-medium">Why rejected:</span> {alt.why_rejected}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dissent */}
        {decision.dissent.length > 0 && (
          <div className="glass rounded-xl p-6 mb-6 border-l-4 border-amber-400">
            <h2 className="text-lg font-display font-bold mb-3 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-amber-500" />
              Dissent & Concerns
              <span className="text-sm font-normal text-gray-500">
                ({decision.dissent.filter(d => d.status === 'open').length} open)
              </span>
            </h2>
            <div className="space-y-4">
              {decision.dissent.map((d) => (
                <div key={d.id} className="p-4 bg-amber-50 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-amber-900">{d.person}</p>
                      <p className="text-amber-800 mt-1">{d.concern}</p>
                      {d.reasoning && (
                        <p className="text-sm text-amber-700 mt-2 italic">"{d.reasoning}"</p>
                      )}
                    </div>
                    <div className="flex-shrink-0 ml-4">
                      {getDissentStatusIcon(d.status)}
                    </div>
                  </div>
                  {d.resolution && (
                    <div className="mt-3 pt-3 border-t border-amber-200">
                      <p className="text-sm text-amber-700">
                        <span className="font-medium">Resolution:</span> {d.resolution}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Uncertainty */}
        {decision.uncertainty.length > 0 && (
          <div className="glass rounded-xl p-6 mb-6 border-l-4 border-purple-400">
            <h2 className="text-lg font-display font-bold mb-3 flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-purple-500" />
              Uncertainty & Assumptions
              <span className="text-sm font-normal text-gray-500">
                ({decision.uncertainty.filter(u => u.status === 'open').length} open)
              </span>
            </h2>
            <div className="space-y-4">
              {decision.uncertainty.map((u) => (
                <div key={u.id} className="p-4 bg-purple-50 rounded-lg">
                  <p className="font-semibold text-purple-900">{u.aspect}</p>
                  <p className="text-purple-800 mt-1">{u.description}</p>
                  {u.impact_if_wrong && (
                    <p className="text-sm text-purple-700 mt-2">
                      <span className="font-medium">Impact if wrong:</span> {u.impact_if_wrong}
                    </p>
                  )}
                  {u.mitigation && (
                    <p className="text-sm text-purple-700 mt-1">
                      <span className="font-medium">Mitigation:</span> {u.mitigation}
                    </p>
                  )}
                  {u.resolution && (
                    <div className="mt-3 pt-3 border-t border-purple-200">
                      <p className="text-sm text-purple-700">
                        <span className="font-medium">Resolution:</span> {u.resolution}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Outcomes */}
        {decision.outcomes.length > 0 && (
          <div className="glass rounded-xl p-6 mb-6">
            <h2 className="text-lg font-display font-bold mb-3 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              Recorded Outcomes
            </h2>
            <div className="space-y-3">
              {decision.outcomes.map((o) => (
                <div key={o.id} className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-gray-900">{o.description}</p>
                  <p className="text-sm text-gray-500 mt-2">{formatDate(o.recorded_at)}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-center gap-4 mt-8">
          <Link
            href="/"
            className="px-4 py-2 bg-brand-600 text-white rounded-lg font-semibold hover:bg-brand-700 transition-colors"
          >
            Ask Julian about this decision
          </Link>
        </div>
      </main>
    </div>
  )
}
