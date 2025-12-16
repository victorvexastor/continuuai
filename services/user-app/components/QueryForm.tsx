'use client'

import { Search, BookOpen, Lightbulb, Rocket } from 'lucide-react'
import { QueryMode } from '@/lib/types'

interface QueryFormProps {
  query: string
  mode: QueryMode
  loading: boolean
  onQueryChange: (query: string) => void
  onModeChange: (mode: QueryMode) => void
  onSubmit: () => void
}

const MODES: { value: QueryMode; label: string; description: string; Icon: any }[] = [
  { value: 'recall', label: 'Recall', description: 'Retrieve past decisions', Icon: BookOpen },
  { value: 'reflection', label: 'Reflection', description: 'Analyze patterns', Icon: Lightbulb },
  { value: 'projection', label: 'Projection', description: 'Explore scenarios', Icon: Rocket },
]

export function QueryForm({
  query,
  mode,
  loading,
  onQueryChange,
  onModeChange,
  onSubmit,
}: QueryFormProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim() && !loading) {
      onSubmit()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="glass rounded-2xl p-6 sm:p-8 backdrop-blur-xl shadow-xl">
      <div className="mb-6">
        <label className="block text-sm font-bold text-gray-900 dark:text-gray-100 mb-3 font-display">
          Query Mode
        </label>
        <div className="flex flex-wrap gap-3">
          {MODES.map((m) => {
            const Icon = m.Icon
            return (
              <button
                key={m.value}
                type="button"
                onClick={() => onModeChange(m.value)}
                className={`
                  group px-5 py-3 rounded-xl font-semibold transition-all duration-300 transform flex items-center gap-2
                  ${mode === m.value
                    ? 'bg-gradient-brand text-white shadow-glow hover:shadow-glow-lg scale-105'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200 hover:scale-105'
                  }
                `}
                title={m.description}
              >
                <Icon className="w-5 h-5" />
                {m.label}
              </button>
            )
          })}
        </div>
        <p className="mt-3 text-sm text-gray-600 flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {MODES.find(m => m.value === mode)?.description}
        </p>
      </div>

      <div className="mb-6">
        <label htmlFor="query" className="block text-sm font-bold text-gray-900 dark:text-gray-100 mb-3 font-display">
          Your Question
        </label>
        <div className="relative">
          <textarea
            id="query"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            rows={4}
            placeholder="What do you want to know? Ask about decisions, context, or future scenarios..."
            className="
              w-full px-5 py-4 
              bg-white/50 dark:bg-gray-800/50 
              border-2 border-gray-200 dark:border-gray-700
              rounded-xl
              focus:ring-2 focus:ring-brand-500 focus:border-brand-500
              dark:focus:ring-brand-400 dark:focus:border-brand-400
              transition-all duration-300
              resize-none
              placeholder:text-gray-400 dark:placeholder:text-gray-500
              text-gray-900 dark:text-gray-100
              hover:border-gray-300 dark:hover:border-gray-600
            "
            disabled={loading}
          />
          <div className="absolute bottom-3 right-3 text-xs text-gray-400 dark:text-gray-500">
            {query.length} characters
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading || !query.trim()}
        className="
          w-full 
          bg-gradient-brand
          text-white px-8 py-4 rounded-xl 
          font-bold text-lg
          hover:shadow-glow-lg
          disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none
          transition-all duration-300
          flex items-center justify-center gap-3
          group
          hover:scale-[1.02]
          active:scale-[0.98]
        "
      >
        {loading ? (
          <>
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white" />
            <span>Searching memory...</span>
          </>
        ) : (
          <>
            <Search className="w-6 h-6 group-hover:scale-110 transition-transform" />
            <span>Search Memory</span>
          </>
        )}
      </button>
    </form>
  )
}
