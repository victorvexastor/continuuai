'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Terminal, Sparkles } from 'lucide-react'

export function AdminNav() {
    const pathname = usePathname()

    const navItems = [
        { href: '/', label: 'Dashboard', icon: LayoutDashboard },
        { href: '/dev', label: 'Dev Controller', icon: Terminal },
    ]

    return (
        <header className="glass-strong border-b border-gray-200 sticky top-0 z-50 mb-8">
            <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
                <Link href="/" className="flex items-center gap-3 group hover:scale-105 transition-transform">
                    <div className="relative">
                        <div className="absolute inset-0 bg-gradient-brand rounded-xl blur-md opacity-50 group-hover:opacity-75 transition-opacity"></div>
                        <div className="relative p-2 bg-gradient-brand rounded-xl shadow-glow">
                            <Sparkles className="w-6 h-6 text-white" />
                        </div>
                    </div>
                    <div>
                        <h1 className="text-xl font-display font-bold gradient-text">ContinuuAI Admin</h1>
                        <p className="text-xs text-gray-600">System Management</p>
                    </div>
                </Link>

                <nav className="flex items-center gap-2">
                    {navItems.map((item) => {
                        const Icon = item.icon
                        const isActive = pathname === item.href
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`
                  flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold transition-all
                  ${isActive
                                        ? 'bg-gradient-brand text-white shadow-glow'
                                        : 'text-gray-700 hover:bg-gray-100 hover:scale-105'
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
