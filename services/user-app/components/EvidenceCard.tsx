'use client'

import { useState } from 'react'
import { Copy, Check, ExternalLink } from 'lucide-react'
import { Evidence } from '@/lib/types'

interface EvidenceCardProps {
  evidence: Evidence
  index: number
}

export function EvidenceCard({ evidence, index }: EvidenceCardProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(evidence.quote)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API not available
    }
  }

  const confidencePercent = Math.round(evidence.confidence * 100)
  const confidenceColor =
    confidencePercent >= 80 ? 'from-green-500 to-emerald-500' :
      confidencePercent >= 60 ? 'from-yellow-500 to-orange-500' :
        'from-orange-500 to-red-500'

  const borderColor =
    confidencePercent >= 80 ? 'border-green-200 dark:border-green-800' :
      confidencePercent >= 60 ? 'border-yellow-200 dark:border-yellow-800' :
        'border-orange-200 dark:border-orange-800'

  return (
    <div className={`
      glass rounded-xl p-5 border-2 ${borderColor}
      group hover:shadow-glow transition-all duration-300 hover:-translate-y-1
      animate-slide-up
    `} style={{ animationDelay: `${index * 0.1}s` }}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="relative w-12 h-12">
            {/* Circular progress indicator */}
            <svg className="transform -rotate-90" width="48" height="48">
              <circle
                cx="24"
                cy="24"
                r="20"
                stroke="currentColor"
                strokeWidth="3"
                fill="none"
                className="text-gray-200 dark:text-gray-700"
              />
              <circle
                cx="24"
                cy="24"
                r="20"
                stroke="url(#gradient-${index})"
                strokeWidth="3"
                fill="none"
                strokeDasharray={`${2 * Math.PI * 20}`}
                strokeDashoffset={`${2 * Math.PI * 20 * (1 - evidence.confidence)}`}
                className="transition-all duration-1000"
                strokeLinecap="round"
              />
              <defs>
                <linearGradient id={`gradient-${index}`} x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" className={`${confidenceColor.split(' ')[0].replace('from-', 'text-')}`} stopColor="currentColor" />
                  <stop offset="100%" className={`${confidenceColor.split(' ')[1].replace('to-', 'text-')}`} stopColor="currentColor" />
                </linearGradient>
              </defs>
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-bold text-gray-900 dark:text-gray-100">{confidencePercent}%</span>
            </div>
          </div>
          <div>
            <span className="text-sm font-bold text-gray-900 dark:text-gray-100 font-display">
              Evidence {index + 1}
            </span>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Confidence Score
            </p>
          </div>
        </div>
        <button
          onClick={handleCopy}
          className="
            p-2 rounded-lg 
            bg-gray-100 dark:bg-gray-800/50 
            hover:bg-gradient-brand hover:text-white
            transition-all duration-300
            opacity-0 group-hover:opacity-100
            hover:scale-110
          "
          title="Copy quote"
        >
          {copied ? (
            <Check className="w-4 h-4" />
          ) : (
            <Copy className="w-4 h-4" />
          )}
        </button>
      </div>

      <blockquote className="
        relative text-sm text-gray-800 dark:text-gray-200 leading-relaxed
        pl-6 pr-4 py-3 my-4
        border-l-4 border-gradient-brand
        bg-gradient-to-r from-gray-50/50 to-transparent
        dark:from-gray-800/30 dark:to-transparent
        rounded-r-lg
      ">
        <span className="absolute -left-1 -top-2 text-4xl text-brand-400 dark:text-brand-600 font-serif">"</span>
        {evidence.quote}
        <span className="absolute -right-2 -bottom-4 text-4xl text-brand-400 dark:text-brand-600 font-serif">"</span>
      </blockquote>

      {evidence.artifact_id && (
        <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <ExternalLink className="w-3.5 h-3.5" />
          <span className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
            {evidence.artifact_id.slice(0, 12)}...
          </span>
        </div>
      )}
    </div>
  )
}
