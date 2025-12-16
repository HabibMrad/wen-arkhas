/**
 * API Client for Wen-Arkhas Backend
 *
 * Handles all communication with the backend API endpoints:
 * - POST /api/search - Standard search
 * - GET /api/search/stream - Streaming search
 * - GET /api/search/{id} - Cached results
 * - GET /health - Health check
 */

import axios, { AxiosInstance } from 'axios'

// Types
export interface Location {
  lat: number
  lng: number
}

export interface SearchRequest {
  query: string
  location: Location
}

export interface Product {
  product_id: string
  store_id: string
  title: string
  price: number
  currency: string
  rating?: number
  reviews_count?: number
  availability: boolean
  url: string
  image_url?: string | null
  specs?: Record<string, string> | null
  similarity_score: number
  store_name: string
  distance_km: number
}

export interface Recommendation {
  rank: number
  product_id: string
  category: string
  pros: string[]
  cons: string[]
  reasoning?: string
}

export interface PriceAnalysis {
  min_price: number
  max_price: number
  average_price: number
  median_price: number
  currency: string
}

export interface Analysis {
  best_value?: {
    product_id: string
    reasoning: string
  }
  top_3_recommendations: Recommendation[]
  price_analysis: PriceAnalysis
  summary: string
}

export interface SearchResponse {
  search_id: string
  query: string
  location: Location
  stores_found: number
  products_found: number
  results: Product[]
  analysis?: Analysis
  cached: boolean
  execution_time_ms: Record<string, number>
  timestamp: string
}

export interface StreamEvent {
  search_id: string
  status: 'in_progress' | 'complete' | 'error'
  node?: string
  data: Record<string, any>
  message?: string
}

export interface HealthCheckResponse {
  status: string
  version: string
  timestamp: string
}

// API Client Class
class APIClient {
  private client: AxiosInstance
  private baseURL: string

  constructor(baseURL?: string) {
    // Use provided baseURL, or read from environment variable, or default to localhost
    this.baseURL = baseURL ||
      (typeof window === 'undefined'
        ? process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
        : process.env.NEXT_PUBLIC_BACKEND_URL || window.location.origin)

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    try {
      const response = await this.client.get('/health')
      return response.data
    } catch (error) {
      console.error('Health check failed:', error)
      throw error
    }
  }

  /**
   * Standard search - returns complete results
   */
  async search(request: SearchRequest): Promise<SearchResponse> {
    try {
      const response = await this.client.post('/api/search', request)
      return response.data
    } catch (error) {
      console.error('Search failed:', error)
      throw error
    }
  }

  /**
   * Streaming search - returns real-time progress updates
   * Yields events as they arrive from the server
   */
  async *streamSearch(request: SearchRequest): AsyncGenerator<StreamEvent, void, unknown> {
    const { query, location } = request
    const params = new URLSearchParams({
      query,
      lat: location.lat.toString(),
      lng: location.lng.toString(),
    })

    try {
      const response = await fetch(
        `${this.baseURL}/api/search/stream?${params}`,
        {
          method: 'GET',
          headers: {
            'Accept': 'application/x-ndjson',
          },
        }
      )

      if (!response.ok) {
        throw new Error(`Stream error: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')

        // Process complete lines
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim()
          if (line) {
            try {
              const event: StreamEvent = JSON.parse(line)
              yield event
            } catch (e) {
              console.error('Failed to parse stream event:', e)
            }
          }
        }

        // Keep incomplete line in buffer
        buffer = lines[lines.length - 1]
      }

      // Process any remaining data
      if (buffer.trim()) {
        try {
          const event: StreamEvent = JSON.parse(buffer)
          yield event
        } catch (e) {
          console.error('Failed to parse final stream event:', e)
        }
      }
    } catch (error) {
      console.error('Stream search failed:', error)
      throw error
    }
  }

  /**
   * Retrieve cached search result by ID
   */
  async getSearchResult(searchId: string): Promise<SearchResponse> {
    try {
      const response = await this.client.get(`/api/search/${searchId}`)
      return response.data
    } catch (error) {
      console.error('Get search result failed:', error)
      throw error
    }
  }

  /**
   * Check if search result is available
   */
  async getSearchProgress(searchId: string): Promise<{ available: boolean; timestamp: string }> {
    try {
      const response = await this.client.get(`/api/search/${searchId}/progress`)
      return response.data
    } catch (error) {
      console.error('Get search progress failed:', error)
      throw error
    }
  }
}

// Singleton instance
let apiClient: APIClient

export function getAPIClient(baseURL?: string): APIClient {
  if (!apiClient) {
    apiClient = new APIClient(baseURL)
  }
  return apiClient
}

export default APIClient
