import type { Metadata, ReactNode } from 'next'
import { Toaster } from 'sonner'
import './globals.css'

export const metadata: Metadata = {
  title: 'Wen-Arkhas - Find the Cheapest Products Near You',
  description: 'AI-powered local price comparison platform for Lebanon. Find the best deals on products near your location.',
  keywords: ['price comparison', 'shopping', 'Lebanon', 'local stores', 'AI'],
  viewport: 'width=device-width, initial-scale=1.0',
  openGraph: {
    title: 'Wen-Arkhas - Price Comparison Platform',
    description: 'Find the cheapest products near you in Lebanon',
    type: 'website',
  },
}

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-white text-gray-900 dark:bg-gray-950 dark:text-gray-50">
        <div className="min-h-screen flex flex-col">
          {children}
        </div>
        <Toaster position="bottom-right" />
      </body>
    </html>
  )
}
