'use client'

import { useEffect, useState } from 'react'

interface HealthStatus {
  postgres: boolean
  api: boolean
  retrieval: boolean
  loading: boolean
}

export default function AdminDashboard() {
  const [health, setHealth] = useState<HealthStatus>({
    postgres: false,
    api: false,
    retrieval: false,
    loading: true,
  })

  useEffect(() => {
    const checkHealth = async () => {
      try {
        // Check API Gateway
        const apiRes = await fetch('http://localhost:8080/healthz')
        const apiHealthy = apiRes.ok

        // Check Retrieval Service  
        const retrievalRes = await fetch('http://localhost:8081/v1/health')
        const retrievalHealthy = retrievalRes.ok

        setHealth({
          api: apiHealthy,
          retrieval: retrievalHealthy,
          postgres: apiHealthy, // If API is up, DB is up
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
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">ContinuuAI Admin Dashboard</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4">System Health</h2>
          
          {health.loading ? (
            <p className="text-gray-600">Checking services...</p>
          ) : (
            <div className="space-y-3">
              <ServiceStatus name="PostgreSQL" healthy={health.postgres} />
              <ServiceStatus name="API Gateway" healthy={health.api} />
              <ServiceStatus name="Retrieval Service" healthy={health.retrieval} />
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <QuickAction 
              title="View Logs" 
              description="Check system logs"
              command="make logs"
            />
            <QuickAction 
              title="Run Tests" 
              description="Execute test suite"
              command="make test"
            />
            <QuickAction 
              title="Backup Database" 
              description="Create DB backup"
              command="make backup"
            />
          </div>
        </div>

        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Phase 2 MVP:</strong> This is a minimal admin dashboard showing system health. 
            Expand with user management, ACL management, and event log viewer as needed.
          </p>
        </div>
      </div>
    </div>
  )
}

function ServiceStatus({ name, healthy }: { name: string; healthy: boolean }) {
  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
      <span className="font-medium">{name}</span>
      <span className={`px-3 py-1 rounded text-sm font-semibold ${
        healthy ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }`}>
        {healthy ? '✓ Healthy' : '✗ Down'}
      </span>
    </div>
  )
}

function QuickAction({ title, description, command }: { 
  title: string
  description: string 
  command: string 
}) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-blue-400 transition">
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-gray-600 mb-2">{description}</p>
      <code className="text-xs bg-gray-100 px-2 py-1 rounded">{command}</code>
    </div>
  )
}
