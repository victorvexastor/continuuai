import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ContinuuAI - Organizational Memory',
  description: 'Evidence-based decision intelligence for your organization',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
