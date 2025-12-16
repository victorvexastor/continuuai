'use client'

import { formatDistanceToNow } from 'date-fns'
import { Clock, Trash2, RotateCcw } from 'lucide-react'
import { HistoryItem, QueryMode } from '@/lib/types'

interface HistoryListProps {
  items: HistoryItem[]
  onSelect: (item: HistoryItem) => void
  onDelete: (id: string) => void
  compact?: boolean
}

const modeColors: Record<QueryMode, string> = {
  recall: 'bg-blue-100 text-blue-800',
  reflection: 'bg-purple-100 text-purple-800',
  projection: 'bg-green-100 text-green-800',
}

export function HistoryList({ items, onSelect, onDelete, compact = false }: HistoryListProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Clock className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p>No history yet</p>
        <p className="text-sm">Your queries will appear here</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.id}
          className="group bg-gray-50 hover:bg-gray-100 rounded-lg p-3 transition cursor-pointer"
          onClick={() => onSelect(item)}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${modeColors[item.mode]}`}>
                  {item.mode}
                </span>
                <span className="text-xs text-gray-400">
                  {formatDistanceToNow(item.timestamp, { addSuffix: true })}
                </span>
              </div>
              <p className={`text-sm text-gray-700 ${compact ? 'truncate' : 'line-clamp-2'}`}>
                {item.query}
              </p>
              {!compact && (
                <p className="text-xs text-gray-500 mt-1 truncate">
                  {item.response.evidence.length} source{item.response.evidence.length !== 1 ? 's' : ''}
                </p>
              )}
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onSelect(item)
                }}
                className="p-1.5 hover:bg-brand-100 rounded transition"
                title="Load this query"
              >
                <RotateCcw className="w-4 h-4 text-brand-600" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(item.id)
                }}
                className="p-1.5 hover:bg-red-100 rounded transition"
                title="Delete"
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
