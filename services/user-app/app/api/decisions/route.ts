import { NextRequest, NextResponse } from 'next/server'

// Use SERVER_API_URL for server-side routes (internal Docker network)
// Falls back to NEXT_PUBLIC_API_URL for local development
const API_URL = process.env.SERVER_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'
// TODO: Get from auth context in production
const DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000000'
const DEFAULT_PRINCIPAL_ID = 'ad4e8240-683e-40a8-a00d-6d5c7c5bb32b'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Add org_id and principal_id from auth context
    const enrichedBody = {
      ...body,
      org_id: body.org_id || DEFAULT_ORG_ID,
      principal_id: body.principal_id || DEFAULT_PRINCIPAL_ID,
    }
    
    const response = await fetch(`${API_URL}/v1/decisions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(enrichedBody),
    })

    const data = await response.json()

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Decision recording error:', error)
    return NextResponse.json(
      { error: 'Failed to record decision' },
      { status: 500 }
    )
  }
}

export async function GET() {
  // Get decision streams for dropdown
  try {
    const response = await fetch(`${API_URL}/v1/streams?org_id=${DEFAULT_ORG_ID}`)
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching streams:', error)
    return NextResponse.json(
      { error: 'Failed to fetch streams' },
      { status: 500 }
    )
  }
}
