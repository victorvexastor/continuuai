'use client'

import { QueryResponse } from '@/lib/types'
import { EvidenceCard } from './EvidenceCard'

interface AnswerDisplayProps {
  response: QueryResponse
}

export function AnswerDisplay({ response }: AnswerDisplayProps) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="mb-4 flex items-center gap-2">
        <span className="inline-block px-3 py-1 bg-brand-100 text-brand-800 rounded-full text-sm font-semibold">
          {response.mode} mode
        </span>
        {response.policy.status && (
          <span className="inline-block px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-xs">
            {response.policy.status}
          </span>
        )}
      </div>

      {/* Decision Card */}
      {response.decision_card && (
        <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-600 rounded">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Decision</h2>
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-gray-600">What was decided</h3>
              <p className="text-gray-900">{response.decision_card.what}</p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-600">Why (reasoning & tradeoffs)</h3>
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{response.decision_card.why}</p>
            </div>
            <div className="flex gap-6 text-sm">
              <div>
                <span className="font-semibold text-gray-600">Who: </span>
                <span className="text-gray-700">{response.decision_card.who}</span>
              </div>
              <div>
                <span className="font-semibold text-gray-600">When: </span>
                <span className="text-gray-700">{response.decision_card.when}</span>
              </div>
              {response.decision_card.stream && (
                <div>
                  <span className="font-semibold text-gray-600">Stream: </span>
                  <span className="text-gray-700">{response.decision_card.stream}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Dissent Section - Highlighted */}
      {response.dissent && response.dissent.length > 0 && (
        <div className="mb-6 p-4 bg-amber-50 border-l-4 border-amber-600 rounded">
          <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
            <span>⚠️</span>
            <span>Dissent & Concerns</span>
          </h3>
          <div className="space-y-3">
            {response.dissent.map((item, idx) => (
              <div key={idx} className="border-l-2 border-amber-300 pl-3">
                <p className="text-sm font-semibold text-gray-700">{item.person}</p>
                <p className="text-gray-700">{item.concern}</p>
                {item.timestamp && (
                  <p className="text-xs text-gray-500 mt-1">{item.timestamp}</p>
                )}
              </div>
            ))}
          </div>
          <p className="text-xs text-amber-700 mt-3 italic">
            This dissent was preserved intentionally. It may contain valuable foresight.
          </p>
        </div>
      )}

      {/* Uncertainty Section */}
      {response.uncertainty && response.uncertainty.length > 0 && (
        <div className="mb-6 p-4 bg-purple-50 border-l-4 border-purple-600 rounded">
          <h3 className="text-lg font-bold text-gray-900 mb-3">Uncertainty & Open Questions</h3>
          <div className="space-y-3">
            {response.uncertainty.map((item, idx) => (
              <div key={idx}>
                <p className="text-sm font-semibold text-gray-700">{item.aspect}</p>
                <p className="text-gray-700">{item.description}</p>
                {item.should_revisit && (
                  <p className="text-xs text-purple-700 mt-1">
                    <strong>Revisit:</strong> {item.should_revisit}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Decisions */}
      {response.related_decisions && response.related_decisions.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-bold text-gray-900 mb-3">Related Decisions</h3>
          <div className="space-y-2">
            {response.related_decisions.map((dec) => (
              <div key={dec.decision_id} className="p-3 border border-gray-200 rounded hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-semibold text-gray-900">{dec.title}</p>
                    <p className="text-sm text-gray-600">{dec.summary}</p>
                  </div>
                  <div className="text-xs text-gray-500">
                    <p>{dec.date}</p>
                    <p className="text-brand-600">{dec.relationship}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fallback to generic answer if no decision card */}
      {!response.decision_card && (
        <div className="mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Answer</h2>
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {response.answer}
          </p>
        </div>
      )}

      {response.evidence.length > 0 && (
        <div>
          <h3 className="text-lg font-bold text-gray-900 mb-3">
            Evidence ({response.evidence.length} source{response.evidence.length !== 1 ? 's' : ''})
          </h3>
          <div className="space-y-3">
            {response.evidence.map((ev, idx) => (
              <EvidenceCard key={ev.evidence_span_id || idx} evidence={ev} index={idx} />
            ))}
          </div>
        </div>
      )}

      {response.policy.notes && response.policy.notes.length > 0 && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <h4 className="text-sm font-semibold text-gray-600 mb-2">Policy Notes</h4>
          <ul className="text-sm text-gray-500 list-disc list-inside">
            {response.policy.notes.map((note, idx) => (
              <li key={idx}>{note}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          Contract: {response.contract_version}
        </p>
      </div>
    </div>
  )
}
