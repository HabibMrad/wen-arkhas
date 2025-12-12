/**
 * SearchInput Component
 *
 * Main search interface with:
 * - Query input field
 * - Location picker (current location or coordinates)
 * - Search button with loading state
 * - Recent queries suggestions
 */

'use client'

import { useState, useEffect } from 'react'
import { useLocation } from '@/hooks/useSearch'
import { useSearchStore } from '@/store/searchStore'
import { MagnifyingGlassIcon, MapPinIcon } from '@heroicons/react/24/outline'

interface SearchInputProps {
  onSearch: (query: string, location: { lat: number; lng: number }) => Promise<void>
  isLoading?: boolean
  placeholder?: string
}

export function SearchInput({
  onSearch,
  isLoading = false,
  placeholder = 'Search for products (e.g., "Nike shoes size 42")',
}: SearchInputProps) {
  const [query, setQuery] = useState('')
  const [showRecentQueries, setShowRecentQueries] = useState(false)
  const { location, getCurrentLocation, error: locationError } = useLocation()
  const recentQueries = useSearchStore((state) => state.recentQueries)
  const addRecentQuery = useSearchStore((state) => state.addRecentQuery)
  const userLocation = useSearchStore((state) => state.userLocation)
  const setUserLocation = useSearchStore((state) => state.setUserLocation)
  const defaultLocation = useSearchStore((state) => state.defaultLocation)

  const currentLocation = location || userLocation || defaultLocation
  const [customLat, setCustomLat] = useState<string>('')
  const [customLng, setCustomLng] = useState<string>('')

  useEffect(() => {
    if (currentLocation) {
      setCustomLat(currentLocation.lat.toFixed(4))
      setCustomLng(currentLocation.lng.toFixed(4))
    }
  }, [currentLocation])

  const handleSearch = async (searchQuery?: string) => {
    const queryToSearch = searchQuery || query

    if (!queryToSearch.trim()) {
      alert('Please enter a search query')
      return
    }

    if (!currentLocation) {
      alert('Please set your location')
      return
    }

    try {
      addRecentQuery(queryToSearch)
      await onSearch(queryToSearch, currentLocation)
      setQuery('')
      setShowRecentQueries(false)
    } catch (error) {
      console.error('Search error:', error)
    }
  }

  const handleLocationChange = () => {
    const lat = parseFloat(customLat)
    const lng = parseFloat(customLng)

    if (isNaN(lat) || isNaN(lng)) {
      alert('Please enter valid coordinates')
      return
    }

    if (lat < 33.0 || lat > 34.7 || lng < 35.1 || lng > 36.6) {
      alert('Location must be within Lebanon boundaries')
      return
    }

    setUserLocation({ lat, lng })
  }

  return (
    <div className="w-full space-y-4">
      {/* Search Input */}
      <div className="relative">
        <div className="relative flex items-center">
          <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setShowRecentQueries(true)
            }}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            onFocus={() => setShowRecentQueries(true)}
            placeholder={placeholder}
            className="w-full pl-12 pr-4 py-3 rounded-lg border border-gray-300 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 outline-none transition-all duration-200"
          />
        </div>

        {/* Recent Queries Dropdown */}
        {showRecentQueries && recentQueries.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
            {recentQueries.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSearch(q)}
                className="w-full text-left px-4 py-2 hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg transition-colors duration-150"
              >
                <div className="flex items-center gap-2">
                  <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-700">{q}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Location Selector */}
      <div className="space-y-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPinIcon className="h-5 w-5 text-primary-600" />
            <span className="font-medium text-gray-900">Location</span>
          </div>
          <button
            onClick={getCurrentLocation}
            disabled={isLoading}
            className="px-3 py-1 text-sm bg-primary-100 text-primary-700 rounded hover:bg-primary-200 transition-colors duration-150 disabled:opacity-50"
          >
            📍 Current
          </button>
        </div>

        {/* Location Display */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Latitude
            </label>
            <input
              type="text"
              value={customLat}
              onChange={(e) => setCustomLat(e.target.value)}
              onBlur={handleLocationChange}
              placeholder="33.89"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Longitude
            </label>
            <input
              type="text"
              value={customLng}
              onChange={(e) => setCustomLng(e.target.value)}
              onBlur={handleLocationChange}
              placeholder="35.50"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none"
            />
          </div>
        </div>

        {locationError && (
          <p className="text-sm text-red-600">{locationError}</p>
        )}
        {currentLocation && !locationError && (
          <p className="text-xs text-gray-600">
            📍 {currentLocation.lat.toFixed(4)}, {currentLocation.lng.toFixed(4)}
          </p>
        )}
      </div>

      {/* Search Button */}
      <button
        onClick={() => handleSearch()}
        disabled={isLoading || !query.trim() || !currentLocation}
        className="w-full py-3 px-4 bg-gradient-to-r from-primary-600 to-primary-700 text-white font-semibold rounded-lg hover:from-primary-700 hover:to-primary-800 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
            Searching...
          </>
        ) : (
          <>
            <MagnifyingGlassIcon className="h-5 w-5" />
            Search Products
          </>
        )}
      </button>
    </div>
  )
}
