'use client'

import { useState } from 'react'

interface RecordDecisionProps {
  onSubmit: (decision: DecisionRequest) => Promise<void>
  streams: DecisionStream[]
}

interface DecisionStream {
  id: string
  name: string
}

interface DissentItem {
  person: string
  concern: string
  reasoning: string
}

interface UncertaintyItem {
  aspect: string
  description: string
  impact_if_wrong: string
  mitigation: string
}

interface FormData {
  title: string
  what_decided: string
  reasoning: string
  dissent_text: string // Free-form input that gets parsed
  uncertainty_text: string // Free-form input that gets parsed
  stream_id: string
  revisit_date: string
}

interface DecisionRequest {
  title: string
  what_decided: string
  reasoning: string
  constraints: string[]
  alternatives: { option: string; why_rejected: string }[]
  dissent: DissentItem[]
  uncertainty: UncertaintyItem[]
  stream_id: string
  revisit_date?: string
}

function parseDissentText(text: string): DissentItem[] {
  if (!text.trim()) return []
  // Simple parsing: each line becomes one dissent item
  // Format: "Person - Concern" or just free text
  return text.split('\n').filter(l => l.trim()).map(line => {
    const dashMatch = line.match(/^(.+?)\s*-\s*(.+)$/)
    if (dashMatch) {
      return { person: dashMatch[1].trim(), concern: dashMatch[2].trim(), reasoning: '' }
    }
    return { person: 'Unnamed', concern: line.trim(), reasoning: '' }
  })
}

function parseUncertaintyText(text: string): UncertaintyItem[] {
  if (!text.trim()) return []
  // Each paragraph or line becomes one uncertainty item
  return text.split('\n').filter(l => l.trim()).map(line => ({
    aspect: 'Assumption',
    description: line.trim(),
    impact_if_wrong: '',
    mitigation: ''
  }))
}

export function RecordDecision({ onSubmit, streams }: RecordDecisionProps) {
  const [formData, setFormData] = useState<FormData>({
    title: '',
    what_decided: '',
    reasoning: '',
    dissent_text: '',
    uncertainty_text: '',
    stream_id: streams[0]?.id || '',
    revisit_date: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    try {
      // Transform form data to API format
      const decision: DecisionRequest = {
        title: formData.title || formData.what_decided.slice(0, 80),
        what_decided: formData.what_decided,
        reasoning: formData.reasoning,
        constraints: [],
        alternatives: [],
        dissent: parseDissentText(formData.dissent_text),
        uncertainty: parseUncertaintyText(formData.uncertainty_text),
        stream_id: formData.stream_id,
        ...(formData.revisit_date ? { revisit_date: formData.revisit_date } : {})
      }
      
      await onSubmit(decision)
      setSuccess(true)
      // Reset form
      setFormData({
        title: '',
        what_decided: '',
        reasoning: '',
        dissent_text: '',
        uncertainty_text: '',
        stream_id: streams[0]?.id || '',
        revisit_date: ''
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record decision')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Record a Decision</h2>
        <p className="text-sm text-gray-600">
          Preserve the reasoning, dissent, and uncertainty. Takes ~10 minutes.
        </p>
      </div>

      {success && (
        <div className="mb-6 p-4 bg-green-50 border-l-4 border-green-500 rounded">
          <p className="text-green-800 font-semibold">✓ Decision recorded successfully</p>
          <p className="text-sm text-green-700 mt-1">
            It's now queryable by anyone with permission to this stream.
          </p>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded">
          <p className="text-red-800 font-semibold">Error</p>
          <p className="text-sm text-red-700 mt-1">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Decision Stream */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Decision Stream *
          </label>
          <select
            value={formData.stream_id}
            onChange={(e) => setFormData({ ...formData, stream_id: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            required
          >
            {streams.map((stream) => (
              <option key={stream.id} value={stream.id}>
                {stream.name}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Who can see this decision depends on stream permissions
          </p>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Title (Brief summary)
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            placeholder="E.g., Adopt GraphQL for new API"
          />
          <p className="text-xs text-gray-500 mt-1">
            Optional: Auto-generated from decision text if left blank
          </p>
        </div>

        {/* What was decided */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            What was decided? *
          </label>
          <textarea
            value={formData.what_decided}
            onChange={(e) => setFormData({ ...formData, what_decided: e.target.value })}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
            rows={3}
            placeholder="Example: We will use progressive disclosure for patient data access rather than showing all information at once."
            required
          />
        </div>

        {/* Why - Reasoning & Tradeoffs */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Why? (Reasoning & Tradeoffs) *
          </label>
          <textarea
            value={formData.reasoning}
            onChange={(e) => setFormData({ ...formData, reasoning: e.target.value })}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-none"
            rows={6}
            placeholder="Example: Primary concern was overwhelming patients with clinical terminology they wouldn't understand. We traded comprehensiveness for clarity. Pilot feedback showed 78% preferred seeing basic info first with option to expand. Cost: Some patients may feel information is being hidden."
            required
          />
          <p className="text-xs text-gray-500 mt-1">
            Include constraints, tradeoffs, and what you optimized for
          </p>
        </div>

        {/* Dissent & Concerns */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <span>⚠️</span>
            <span>Dissent & Concerns</span>
          </label>
          <textarea
            value={formData.dissent_text}
            onChange={(e) => setFormData({ ...formData, dissent_text: e.target.value })}
            className="w-full px-4 py-3 border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none bg-amber-50"
            rows={4}
            placeholder="Format each concern on a new line: &#10;Maria Chen - Concerned about paternalism&#10;Jake Martinez - Worried about liability if critical info isn't immediately visible"
          />
          <p className="text-xs text-amber-700 mt-1">
            <strong>Critical:</strong> Preserve who disagreed and why. This may prove valuable later.
          </p>
        </div>

        {/* Uncertainty & Open Questions */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Uncertainty & Open Questions
          </label>
          <textarea
            value={formData.uncertainty_text}
            onChange={(e) => setFormData({ ...formData, uncertainty_text: e.target.value })}
            className="w-full px-4 py-3 border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none bg-purple-50"
            rows={4}
            placeholder="List each assumption or unknown on a new line:&#10;Will this work for chronic condition patients?&#10;Pilot was mostly acute care - behavior may differ"
          />
          <p className="text-xs text-purple-700 mt-1">
            What don't you know? What assumptions are you making? What could invalidate this decision?
          </p>
        </div>

        {/* When to revisit */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            When should we revisit this?
          </label>
          <input
            type="date"
            value={formData.revisit_date}
            onChange={(e) => setFormData({ ...formData, revisit_date: e.target.value })}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-500 mt-1">
            Optional: Set a date to review if assumptions still hold
          </p>
        </div>

        {/* Submit */}
        <div className="pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading}
            className="w-full px-6 py-3 bg-brand-600 text-white rounded-lg font-semibold hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Recording...' : 'Record Decision'}
          </button>
          <p className="text-xs text-gray-500 text-center mt-3">
            This will be immediately queryable by permitted users
          </p>
        </div>
      </form>
    </div>
  )
}
