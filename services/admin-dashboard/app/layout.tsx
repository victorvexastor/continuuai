import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ContinuuAI Admin Dashboard',
  description: 'System management and monitoring',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50">{children}</body>
    </html>
  )
}
