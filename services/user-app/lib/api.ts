import { QueryMode, QueryResponse, QueryRequest } from './types'

const DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000000'
const DEFAULT_PRINCIPAL_ID = 'ad4e8240-683e-40a8-a00d-6d5c7c5bb32b'

export function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
}

export async function submitQuery(
  queryText: string,
  mode: QueryMode,
  options?: {
    orgId?: string
    principalId?: string
    scopes?: string[]
  }
): Promise<QueryResponse> {
  const apiUrl = getApiUrl()
  
  const request: QueryRequest = {
    org_id: options?.orgId || DEFAULT_ORG_ID,
    principal_id: options?.principalId || DEFAULT_PRINCIPAL_ID,
    mode,
    query_text: queryText,
    scopes: options?.scopes || []
  }

  const res = await fetch(`${apiUrl}/v1/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })

  if (!res.ok) {
    const errorText = await res.text().catch(() => 'Unknown error')
    throw new Error(`API error ${res.status}: ${errorText}`)
  }

  return res.json()
}

export async function checkHealth(): Promise<boolean> {
  try {
    const apiUrl = getApiUrl()
    const res = await fetch(`${apiUrl}/healthz`)
    return res.ok
  } catch {
    return false
  }
}
