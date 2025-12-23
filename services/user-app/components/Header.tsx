'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Sparkles, History, Settings, LayoutDashboard, FileText, MessageSquare } from 'lucide-react'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/record', label: 'Record', icon: FileText },
  { href: '/', label: 'Ask Julian', icon: MessageSquare },
  { href: '/history', label: 'History', icon: History },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export function Header() {
  const pathname = usePathname()

  return (
    <header className="glass-strong border-b border-white/20 dark:border-gray-800/50 sticky top-0 z-50 animate-slide-down">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group hover:scale-105 transition-transform duration-300">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-brand rounded-xl blur-md opacity-50 group-hover:opacity-75 transition-opacity"></div>
            <div className="relative p-2 bg-gradient-brand rounded-xl shadow-glow">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-display font-bold gradient-text">ContinuuAI</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">Evidence-First Memory</p>
          </div>
        </Link>

        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-300
                  ${isActive
                    ? 'bg-gradient-brand text-white shadow-glow hover:shadow-glow-lg'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-800/50 hover:scale-105'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
