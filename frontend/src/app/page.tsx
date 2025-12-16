/**
 * Home Page
 *
 * Landing page with:
 * - Hero section
 * - Search input
 * - Recent searches
 * - Key features
 * - CTA
 */

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { SearchInput } from '@/components/SearchInput'
import { useSearchStore } from '@/store/searchStore'
import { useStreamSearch } from '@/hooks/useSearch'
import { SparklesIcon, MapPinIcon, BoltIcon } from '@heroicons/react/24/outline'

export default function HomePage() {
  const router = useRouter()
  const [isSearching, setIsSearching] = useState(false)
  const { streamSearch, result } = useStreamSearch()
  const setCurrentSearch = useSearchStore((state) => state.setCurrentSearch)
  const searchHistory = useSearchStore((state) => state.searchHistory)

  const handleSearch = async (query: string, location: { lat: number; lng: number }) => {
    setIsSearching(true)
    try {
      // Start streaming search
      await streamSearch(query, location)
    } catch (error) {
      console.error('Search error:', error)
      alert('Search failed. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  // Navigate to results when search completes
  useEffect(() => {
    if (result && !isSearching) {
      setCurrentSearch(result)
      router.push('/results')
    }
  }, [result, isSearching, setCurrentSearch, router])

  return (
    <main className="min-h-screen bg-gradient-to-b from-white via-primary-50 to-white">
      {/* Header/Navigation */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-primary-700 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">🔍</span>
            </div>
            <h1 className="text-xl font-bold text-gray-900">Wen-Arkhas</h1>
            <p className="text-xs text-gray-600 hidden sm:block">Find the Cheapest</p>
          </div>
          <nav className="hidden sm:flex gap-6">
            <a href="#features" className="text-sm text-gray-600 hover:text-gray-900">
              Features
            </a>
            <a href="#how-it-works" className="text-sm text-gray-600 hover:text-gray-900">
              How It Works
            </a>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-20">
        <div className="text-center space-y-6 mb-12">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900">
            Find the Cheapest Products
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-primary-700">
              Near You in Lebanon
            </span>
          </h2>
          <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto">
            AI-powered price comparison. Search once, compare across multiple stores, get smart recommendations instantly.
          </p>
        </div>

        {/* Search Box */}
        <div className="max-w-2xl mx-auto mb-12">
          <div className="bg-white p-6 sm:p-8 rounded-2xl shadow-lg border border-gray-200">
            <SearchInput onSearch={handleSearch} isLoading={isSearching} />
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-12">
          <div className="text-center p-4">
            <div className="text-3xl font-bold text-primary-600">5+</div>
            <p className="text-gray-600 text-sm">Store Categories</p>
          </div>
          <div className="text-center p-4">
            <div className="text-3xl font-bold text-primary-600">100k+</div>
            <p className="text-gray-600 text-sm">Products Available</p>
          </div>
          <div className="text-center p-4">
            <div className="text-3xl font-bold text-primary-600">5 sec</div>
            <p className="text-gray-600 text-sm">Average Search Time</p>
          </div>
        </div>
      </section>

      {/* Recent Searches */}
      {searchHistory.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Searches</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {searchHistory.slice(0, 6).map((item) => (
              <button
                key={item.id}
                onClick={() => router.push('/results')}
                className="text-left p-4 bg-white rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-all duration-200"
              >
                <p className="font-medium text-gray-900 truncate">{item.query}</p>
                <p className="text-xs text-gray-600 mt-1">
                  {new Date(item.timestamp).toLocaleDateString()}
                </p>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Features Section */}
      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h3 className="text-3xl font-bold text-gray-900 mb-4">
            Why Choose Wen-Arkhas?
          </h3>
          <p className="text-gray-600">
            Smart features to find the best deals faster
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* Feature 1 */}
          <div className="space-y-3">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
              <SparklesIcon className="h-6 w-6 text-primary-600" />
            </div>
            <h4 className="font-semibold text-gray-900">AI-Powered</h4>
            <p className="text-gray-600 text-sm">
              Claude AI analyzes products and recommends the best value options for your needs.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="space-y-3">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
              <MapPinIcon className="h-6 w-6 text-primary-600" />
            </div>
            <h4 className="font-semibold text-gray-900">Location-Based</h4>
            <p className="text-gray-600 text-sm">
              Find products at nearby stores and see prices, distance, and availability.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="space-y-3">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
              <BoltIcon className="h-6 w-6 text-primary-600" />
            </div>
            <h4 className="font-semibold text-gray-900">Lightning Fast</h4>
            <p className="text-gray-600 text-sm">
              Get results in seconds with real-time progress tracking and streaming updates.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h3 className="text-3xl font-bold text-gray-900 mb-4">
            How It Works
          </h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {['Enter Query', 'Find Stores', 'Scrape Products', 'AI Analysis'].map(
            (step, idx) => (
              <div key={idx} className="text-center">
                <div className="w-12 h-12 mx-auto bg-primary-600 text-white rounded-full flex items-center justify-center font-bold mb-4">
                  {idx + 1}
                </div>
                <p className="font-medium text-gray-900">{step}</p>
              </div>
            )
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-600 text-sm">
            <p>
              &copy; 2025 Wen-Arkhas. All rights reserved. | Made for the Lebanese market
            </p>
          </div>
        </div>
      </footer>
    </main>
  )
}
