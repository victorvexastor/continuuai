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
