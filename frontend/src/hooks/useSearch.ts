/**
 * Custom React hooks for search functionality
 */

import { useState, useCallback, useRef } from 'react'
import { getAPIClient } from '@/lib/api'
import type { SearchResponse, StreamEvent } from '@/lib/api'

// Search state
interface SearchState {
  query: string
  location: { lat: number; lng: number } | null
  isLoading: boolean
  isStreaming: boolean
  error: string | null
  result: SearchResponse | null
  searchId: string | null
}


/**
 * useSearch - Hook for standard search
 * Returns result after all agents complete
 */
export function useSearch() {
  const [state, setState] = useState<SearchState>({
    query: '',
    location: null,
    isLoading: false,
    isStreaming: false,
    error: null,
    result: null,
    searchId: null,
  })

  const apiClient = getAPIClient()

  const search = useCallback(
    async (query: string, location: { lat: number; lng: number }) => {
      setState((prev) => ({
        ...prev,
        isLoading: true,
        error: null,
        query,
        location,
      }))

      try {
        const result = await apiClient.search({ query, location })
        setState((prev) => ({
          ...prev,
          isLoading: false,
          result,
          searchId: result.search_id,
        }))
        return result
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Search failed'
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: errorMessage,
        }))
        throw error
      }
    },
    [apiClient]
  )

  const reset = useCallback(() => {
    setState({
      query: '',
      location: null,
      isLoading: false,
      isStreaming: false,
      error: null,
      result: null,
      searchId: null,
    })
  }, [])

  return { ...state, search, reset }
}

/**
 * useStreamSearch - Hook for streaming search with real-time progress
 * Yields events as agents complete their work
 */
export function useStreamSearch() {
  const [state, setState] = useState<SearchState>({
    query: '',
    location: null,
    isLoading: false,
    isStreaming: false,
    error: null,
    result: null,
    searchId: null,
  })

  const [progress, setProgress] = useState<StreamEvent | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const apiClient = getAPIClient()

  const streamSearch = useCallback(
    async (query: string, location: { lat: number; lng: number }) => {
      setState((prev) => ({
        ...prev,
        isLoading: true,
        isStreaming: true,
        error: null,
        query,
        location,
      }))

      abortControllerRef.current = new AbortController()

      try {
        const generator = apiClient.streamSearch({ query, location })

        for await (const event of generator) {
          if (abortControllerRef.current?.signal.aborted) {
            break
          }

          setProgress(event)

          if (event.status === 'error') {
            throw new Error(event.message || 'Stream error')
          }

          // When stream completes, we might get final state
          if (event.status === 'complete') {
            setState((prev) => ({
              ...prev,
              isStreaming: false,
            }))
          }
        }

        setState((prev) => ({
          ...prev,
          isLoading: false,
          isStreaming: false,
        }))
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Stream search failed'
        setState((prev) => ({
          ...prev,
          isLoading: false,
          isStreaming: false,
          error: errorMessage,
        }))
        throw error
      }
    },
    [apiClient]
  )

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort()
    setState((prev) => ({
      ...prev,
      isLoading: false,
      isStreaming: false,
    }))
  }, [])

  const reset = useCallback(() => {
    cancel()
    setState({
      query: '',
      location: null,
      isLoading: false,
      isStreaming: false,
      error: null,
      result: null,
      searchId: null,
    })
    setProgress(null)
  }, [cancel])

  return {
    ...state,
    progress,
    streamSearch,
    cancel,
    reset,
  }
}

/**
 * useLocation - Hook for location management
 * Gets user's current location via geolocation API
 */
export function useLocation() {
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const getCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported')
      return
    }

    setIsLoading(true)
    setError(null)

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        })
        setIsLoading(false)
      },
      (error) => {
        setError(error.message || 'Failed to get location')
        setIsLoading(false)
      }
    )
  }, [])

  const setCustomLocation = useCallback((lat: number, lng: number) => {
    setLocation({ lat, lng })
    setError(null)
  }, [])

  return {
    location,
    error,
    isLoading,
    getCurrentLocation,
    setCustomLocation,
  }
}

/**
 * useSearchCache - Hook for managing cached searches
 */
export function useSearchCache() {
  const [cache, setCache] = useState<Map<string, SearchResponse>>(new Map())
  const apiClient = getAPIClient()

  const getCachedResult = useCallback(
    async (searchId: string) => {
      // Check local cache first
      if (cache.has(searchId)) {
        return cache.get(searchId)!
      }

      // Fetch from server
      try {
        const result = await apiClient.getSearchResult(searchId)
        setCache((prev) => new Map(prev).set(searchId, result))
        return result
      } catch (error) {
        console.error('Failed to retrieve cached result:', error)
        throw error
      }
    },
    [cache, apiClient]
  )

  const cacheResult = useCallback((result: SearchResponse) => {
    setCache((prev) => new Map(prev).set(result.search_id, result))
  }, [])

  const clearCache = useCallback(() => {
    setCache(new Map())
  }, [])

  return {
    cache,
    getCachedResult,
    cacheResult,
    clearCache,
  }
}
