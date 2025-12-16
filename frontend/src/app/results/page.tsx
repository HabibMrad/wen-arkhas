/**
 * Results Page
 *
 * Displays search results with:
 * - Search summary
 * - Filters and sorting
 * - Product grid
 * - Map view
 * - Analysis/Recommendations
 *
 * Shows detailed product matches with store information and pricing.
 */

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSearchStore } from '@/store/searchStore'
import { ProductCard } from '@/components/ProductCard'
import { SearchInput } from '@/components/SearchInput'
import { useStreamSearch } from '@/hooks/useSearch'
import {
  FunnelIcon,
  MapIcon,
  ListBulletIcon,
} from '@heroicons/react/24/outline'

export default function ResultsPage() {
  const router = useRouter()
  const currentSearch = useSearchStore((state) => state.currentSearch)
  const selectedProduct = useSearchStore((state) => state.selectedProduct)
  const filterBy = useSearchStore((state) => state.filterBy)
  const showMap = useSearchStore((state) => state.showMap)
  const toggleMap = useSearchStore((state) => state.toggleMap)
  const setFilterBy = useSearchStore((state) => state.setFilterBy)
  const selectProduct = useSearchStore((state) => state.selectProduct)

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const { streamSearch } = useStreamSearch()
  const [isSearching, setIsSearching] = useState(false)

  if (!currentSearch) {
    return (
      <div className="min-h-screen bg-white py-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            No search results found
          </h2>
          <p className="text-gray-600 mb-8">
            Please perform a search to see results.
          </p>
          <button
            onClick={() => router.push('/')}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Back to Search
          </button>
        </div>
      </div>
    )
  }

  const handleNewSearch = async (
    query: string,
    location: { lat: number; lng: number }
  ) => {
    setIsSearching(true)
    try {
      let finalResult = null
      const generator = streamSearch(query, location)

      for await (const event of generator) {
        if (event.status === 'complete' && event.data) {
          finalResult = event.data
        }
      }

      if (finalResult) {
        const store = useSearchStore.getState()
        store.setCurrentSearch(finalResult)
      }
    } catch (error) {
      console.error('Search error:', error)
      alert('Search failed. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  const sortedProducts = [...currentSearch.results].sort((a, b) => {
    switch (filterBy) {
      case 'price':
        return a.price - b.price
      case 'rating':
        return (b.rating || 0) - (a.rating || 0)
      case 'distance':
        return a.distance_km - b.distance_km
      default:
        return 0
    }
  })

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <button
            onClick={() => router.push('/')}
            className="text-primary-600 hover:text-primary-700 font-medium text-sm mb-4"
          >
            ← Back to Search
          </button>

          {/* Search Bar */}
          <div className="max-w-2xl">
            <SearchInput
              onSearch={handleNewSearch}
              isLoading={isSearching}
              placeholder="Search for something else..."
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Results Summary */}
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-gray-600 text-sm">Query</p>
              <p className="text-lg font-semibold text-gray-900">
                {currentSearch.query}
              </p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Stores Found</p>
              <p className="text-lg font-semibold text-gray-900">
                {currentSearch.stores_found}
              </p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Products Found</p>
              <p className="text-lg font-semibold text-gray-900">
                {currentSearch.products_found}
              </p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Search Time</p>
              <p className="text-lg font-semibold text-gray-900">
                {Object.values(currentSearch.execution_time_ms).reduce((a, b) => a + b, 0)}
                ms
              </p>
            </div>
          </div>
        </div>

        {/* AI Analysis */}
        {currentSearch.analysis && (
          <div className="bg-gradient-to-br from-primary-50 to-secondary-50 rounded-lg border border-primary-200 p-6 mb-8">
            <h3 className="text-lg font-bold text-gray-900 mb-4">✨ AI Recommendations</h3>

            {currentSearch.analysis.best_value && (
              <div className="mb-6 p-4 bg-white rounded-lg border-l-4 border-primary-600">
                <p className="text-sm text-gray-600 font-medium">Best Value</p>
                <p className="text-gray-900 font-semibold mt-1">
                  {currentSearch.analysis.best_value.product_id}
                </p>
                <p className="text-sm text-gray-700 mt-2">
                  {currentSearch.analysis.best_value.reasoning}
                </p>
              </div>
            )}

            {currentSearch.analysis.summary && (
              <p className="text-gray-700 text-sm">
                {currentSearch.analysis.summary}
              </p>
            )}

            {currentSearch.analysis.price_analysis && (
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-white p-3 rounded-lg">
                  <p className="text-xs text-gray-600">Min Price</p>
                  <p className="text-lg font-bold text-gray-900">
                    ${currentSearch.analysis.price_analysis.min_price.toFixed(2)}
                  </p>
                </div>
                <div className="bg-white p-3 rounded-lg">
                  <p className="text-xs text-gray-600">Max Price</p>
                  <p className="text-lg font-bold text-gray-900">
                    ${currentSearch.analysis.price_analysis.max_price.toFixed(2)}
                  </p>
                </div>
                <div className="bg-white p-3 rounded-lg">
                  <p className="text-xs text-gray-600">Average</p>
                  <p className="text-lg font-bold text-gray-900">
                    ${currentSearch.analysis.price_analysis.average_price.toFixed(2)}
                  </p>
                </div>
                <div className="bg-white p-3 rounded-lg">
                  <p className="text-xs text-gray-600">Median</p>
                  <p className="text-lg font-bold text-gray-900">
                    ${currentSearch.analysis.price_analysis.median_price.toFixed(2)}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Controls */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-600" />
            <select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value as 'price' | 'rating' | 'distance')}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
            >
              <option value="price">Sort by Price (Low to High)</option>
              <option value="rating">Sort by Rating (High to Low)</option>
              <option value="distance">Sort by Distance (Closest)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg ${
                viewMode === 'grid'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <ListBulletIcon className="h-5 w-5" />
            </button>
            <button
              onClick={toggleMap}
              className={`p-2 rounded-lg ${
                showMap
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <MapIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Products Grid */}
        {sortedProducts.length > 0 ? (
          <div
            className={
              viewMode === 'grid'
                ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                : 'space-y-4'
            }
          >
            {sortedProducts.map((product) => (
              <ProductCard
                key={product.product_id}
                product={product}
                onSelect={selectProduct}
                isSelected={selectedProduct === product.product_id}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-600 text-lg">No products found</p>
          </div>
        )}
      </div>
    </main>
  )
}
