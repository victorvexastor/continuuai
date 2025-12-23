import { NextRequest, NextResponse } from 'next/server'

// Use SERVER_API_URL for server-side routes (internal Docker network)
// Falls back to NEXT_PUBLIC_API_URL for local development
const API_URL = process.env.SERVER_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
// TODO: Get from auth context in production
const DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000000'

export async function GET(request: NextRequest) {
  try {
    const orgId = request.nextUrl.searchParams.get('org_id') || DEFAULT_ORG_ID
    
    const response = await fetch(`${API_URL}/v1/dashboard?org_id=${orgId}`)
    const data = await response.json()
    
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    
    return NextResponse.json(data)
  } catch (error) {
    console.error('Dashboard fetch error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch dashboard data' },
      { status: 500 }
    )
  }
}
