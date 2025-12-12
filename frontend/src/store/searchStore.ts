/**
 * Global state management using Zustand
 * Manages search state, history, and user preferences
 */

import { create } from 'zustand'
import type { SearchResponse, StreamEvent } from '@/lib/api'

interface SearchHistory {
  id: string
  query: string
  location: { lat: number; lng: number }
  timestamp: string
  result?: SearchResponse
}

interface SearchStore {
  // Search state
  currentSearch: SearchResponse | null
  searchHistory: SearchHistory[]
  recentQueries: string[]

  // Location
  userLocation: { lat: number; lng: number } | null
  defaultLocation: { lat: number; lng: number }

  // UI state
  showMap: boolean
  selectedProduct: string | null
  filterBy: 'price' | 'rating' | 'distance'

  // Actions
  setCurrentSearch: (search: SearchResponse | null) => void
  addToHistory: (history: SearchHistory) => void
  clearHistory: () => void
  addRecentQuery: (query: string) => void
  clearRecentQueries: () => void
  setUserLocation: (location: { lat: number; lng: number }) => void
  setDefaultLocation: (location: { lat: number; lng: number }) => void
  toggleMap: () => void
  selectProduct: (productId: string | null) => void
  setFilterBy: (filter: 'price' | 'rating' | 'distance') => void
}

// Lebanon center coordinates (Beirut)
const DEFAULT_LOCATION = { lat: 33.8886, lng: 35.4955 }

export const useSearchStore = create<SearchStore>((set) => ({
  // Initial state
  currentSearch: null,
  searchHistory: [],
  recentQueries: [],
  userLocation: null,
  defaultLocation: DEFAULT_LOCATION,
  showMap: false,
  selectedProduct: null,
  filterBy: 'price',

  // Actions
  setCurrentSearch: (search) => set({ currentSearch: search }),

  addToHistory: (history) =>
    set((state) => ({
      searchHistory: [history, ...state.searchHistory].slice(0, 20), // Keep last 20
    })),

  clearHistory: () => set({ searchHistory: [] }),

  addRecentQuery: (query) =>
    set((state) => ({
      recentQueries: [
        query,
        ...state.recentQueries.filter((q) => q !== query),
      ].slice(0, 5), // Keep last 5
    })),

  clearRecentQueries: () => set({ recentQueries: [] }),

  setUserLocation: (location) => set({ userLocation: location }),

  setDefaultLocation: (location) => set({ defaultLocation: location }),

  toggleMap: () => set((state) => ({ showMap: !state.showMap })),

  selectProduct: (productId) => set({ selectedProduct: productId }),

  setFilterBy: (filter) => set({ filterBy: filter }),
}))

// Persist store to localStorage
if (typeof window !== 'undefined') {
  const store = useSearchStore.getState()
  const saved = localStorage.getItem('wen-arkhas-search-store')

  if (saved) {
    try {
      const restored = JSON.parse(saved)
      // Restore non-sensitive data
      if (restored.recentQueries) {
        store.addRecentQuery(restored.recentQueries[0])
      }
      if (restored.userLocation) {
        store.setUserLocation(restored.userLocation)
      }
    } catch (error) {
      console.error('Failed to restore store:', error)
    }
  }

  // Subscribe to changes and save
  useSearchStore.subscribe((state) => {
    localStorage.setItem(
      'wen-arkhas-search-store',
      JSON.stringify({
        recentQueries: state.recentQueries,
        userLocation: state.userLocation,
        filterBy: state.filterBy,
      })
    )
  })
}
