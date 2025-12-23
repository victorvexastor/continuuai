'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Header } from '@/components/Header'
import { 
  AlertTriangle, 
  Clock, 
  MessageSquare, 
  Lightbulb, 
  Plus,
  ChevronRight,
  TrendingUp,
  Users,
  FileText
} from 'lucide-react'

interface AttentionItem {
  type: 'revisit_due' | 'unresolved_dissent' | 'insight'
  severity: 'critical' | 'warning' | 'attention' | 'info'
  title: string
  description: string
  decision_id?: string
  stream?: string
}

interface RecentDecision {
  id: string
  title: string
  decided_at: string
  stream: {
    name: string
    color: string
  }
  decided_by: string
}

interface DashboardStats {
  total_decisions: number
  active_decisions: number
  open_dissent: number
  revisit_due: number
}

interface DashboardData {
  needs_attention: AttentionItem[]
  recent_decisions: RecentDecision[]
  stats: DashboardStats
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function getSeverityStyles(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-50 border-red-200 text-red-800'
    case 'warning':
      return 'bg-amber-50 border-amber-200 text-amber-800'
    case 'attention':
      return 'bg-orange-50 border-orange-200 text-orange-800'
    default:
      return 'bg-blue-50 border-blue-200 text-blue-800'
  }
}

function getTypeIcon(type: string) {
  switch (type) {
    case 'revisit_due':
      return <Clock className="w-5 h-5" />
    case 'unresolved_dissent':
      return <MessageSquare className="w-5 h-5" />
    case 'insight':
      return <Lightbulb className="w-5 h-5" />
    default:
      return <AlertTriangle className="w-5 h-5" />
  }
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/dashboard')
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          setError(data.error)
        } else {
          setData(data)
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen animated-gradient">
        <Header />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-24 bg-gray-200 rounded-xl"></div>
              ))}
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen animated-gradient">
        <Header />
        <main className="max-w-7xl mx-auto px-4 py-8">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6">
            <p className="text-red-800">Error loading dashboard: {error}</p>
          </div>
        </main>
      </div>
    )
  }

  const { needs_attention, recent_decisions, stats } = data!

  return (
    <div className="min-h-screen animated-gradient">
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-display font-bold gradient-text">
              Decision Dashboard
            </h1>
            <p className="text-gray-600 mt-1">
              Your organization's decision memory at a glance
            </p>
          </div>
          <Link
            href="/record"
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg font-semibold hover:bg-brand-700 transition-colors"
          >
            <Plus className="w-5 h-5" />
            Record Decision
          </Link>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="glass rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Decisions</p>
                <p className="text-3xl font-bold text-gray-900">{stats.total_decisions}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>
          
          <div className="glass rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Active</p>
                <p className="text-3xl font-bold text-gray-900">{stats.active_decisions}</p>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>
          
          <div className="glass rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Open Dissent</p>
                <p className="text-3xl font-bold text-amber-600">{stats.open_dissent}</p>
              </div>
              <div className="p-3 bg-amber-100 rounded-lg">
                <Users className="w-6 h-6 text-amber-600" />
              </div>
            </div>
          </div>
          
          <div className="glass rounded-xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Revisit Due</p>
                <p className="text-3xl font-bold text-red-600">{stats.revisit_due}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-lg">
                <Clock className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Needs Attention */}
          <div className="lg:col-span-2">
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-display font-bold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Needs Your Attention
              </h2>
              
              {needs_attention.length === 0 ? (
                <div className="text-center py-8">
                  <div className="inline-block p-4 bg-green-100 rounded-full mb-3">
                    <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-gray-600">All caught up! No items need attention.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {needs_attention.map((item, idx) => (
                    <Link
                      key={idx}
                      href={item.decision_id ? `/decisions/${item.decision_id}` : '#'}
                      className={`block p-4 rounded-lg border ${getSeverityStyles(item.severity)} hover:shadow-md transition-all`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 mt-0.5">
                          {getTypeIcon(item.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold">{item.title}</p>
                          <p className="text-sm opacity-80 mt-1">{item.description}</p>
                          {item.stream && (
                            <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-white/50 rounded-full">
                              {item.stream}
                            </span>
                          )}
                        </div>
                        <ChevronRight className="w-5 h-5 flex-shrink-0 opacity-50" />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Recent Decisions */}
          <div className="lg:col-span-1">
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-display font-bold mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-gray-500" />
                Recent Decisions
              </h2>
              
              {recent_decisions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500 mb-4">No decisions recorded yet</p>
                  <Link
                    href="/record"
                    className="inline-flex items-center gap-2 text-brand-600 font-semibold hover:text-brand-700"
                  >
                    <Plus className="w-4 h-4" />
                    Record your first decision
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {recent_decisions.map((decision) => (
                    <Link
                      key={decision.id}
                      href={`/decisions/${decision.id}`}
                      className="block p-3 rounded-lg hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-200"
                    >
                      <p className="font-medium text-gray-900 truncate">{decision.title}</p>
                      <div className="flex items-center gap-2 mt-1.5 text-sm text-gray-500">
                        <span
                          className="inline-block w-2 h-2 rounded-full"
                          style={{ backgroundColor: decision.stream.color }}
                        />
                        <span className="truncate">{decision.stream.name}</span>
                        <span>•</span>
                        <span>{formatDate(decision.decided_at)}</span>
                      </div>
                    </Link>
                  ))}
                  
                  {recent_decisions.length >= 10 && (
                    <Link
                      href="/history"
                      className="block text-center text-sm text-brand-600 font-medium hover:text-brand-700 pt-2"
                    >
                      View all decisions →
                    </Link>
                  )}
                </div>
              )}
            </div>

            {/* Quick Actions */}
            <div className="glass rounded-xl p-6 mt-6">
              <h2 className="text-xl font-display font-bold mb-4">Quick Actions</h2>
              <div className="space-y-2">
                <Link
                  href="/record"
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="p-2 bg-brand-100 rounded-lg">
                    <Plus className="w-5 h-5 text-brand-600" />
                  </div>
                  <span className="font-medium">Record New Decision</span>
                </Link>
                <Link
                  href="/"
                  className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <MessageSquare className="w-5 h-5 text-purple-600" />
                  </div>
                  <span className="font-medium">Ask Julian</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
