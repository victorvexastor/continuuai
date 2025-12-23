import { NextRequest, NextResponse } from 'next/server'

// Use SERVER_API_URL for server-side routes (internal Docker network)
// Falls back to NEXT_PUBLIC_API_URL for local development
const API_URL = process.env.SERVER_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    
    const response = await fetch(`${API_URL}/v1/decisions/${id}`)
    const data = await response.json()
    
    if (!response.ok) {
      return NextResponse.json(data, { status: response.status })
    }
    
    return NextResponse.json(data)
  } catch (error) {
    console.error('Decision fetch error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch decision' },
      { status: 500 }
    )
  }
}
