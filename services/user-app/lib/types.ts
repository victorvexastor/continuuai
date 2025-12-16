export type QueryMode = 'recall' | 'reflection' | 'projection'

export interface Evidence {
  evidence_span_id: string
  artifact_id: string
  quote: string
  confidence: number
  metadata?: {
    decision_id?: string
    decision_title?: string
    decided_date?: string
    decided_by?: string
  }
}

export interface DissentItem {
  person: string
  concern: string
  timestamp?: string
}

export interface UncertaintyItem {
  aspect: string
  description: string
  should_revisit?: string
}

export interface RelatedDecision {
  decision_id: string
  title: string
  date: string
  relationship: string
  summary: string
}

export interface QueryResponse {
  contract_version: string
  mode: string
  answer: string
  evidence: Evidence[]
  policy: {
    status: string
    notes: string[]
  }
  // Decision-specific fields
  decision_card?: {
    what: string
    why: string
    who: string
    when: string
    stream?: string
  }
  dissent?: DissentItem[]
  uncertainty?: UncertaintyItem[]
  related_decisions?: RelatedDecision[]
}

export interface HistoryItem {
  id: string
  query: string
  mode: QueryMode
  response: QueryResponse
  timestamp: number
}

export interface QueryRequest {
  org_id: string
  principal_id: string
  mode: QueryMode
  query_text: string
  scopes: string[]
}
