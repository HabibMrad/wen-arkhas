/**
 * ProductCard Component
 *
 * Displays a single product with:
 * - Image and title
 * - Price and currency
 * - Rating and reviews
 * - Store and distance
 * - Match score
 * - Action buttons
 */

'use client'

import Image from 'next/image'
import { StarIcon, MapPinIcon } from '@heroicons/react/24/solid'
import { HeartIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline'
import type { Product } from '@/lib/api'

interface ProductCardProps {
  product: Product
  onSelect?: (productId: string) => void
  isSelected?: boolean
}

export function ProductCard({
  product,
  onSelect,
  isSelected = false,
}: ProductCardProps) {
  const matchPercentage = Math.round(product.similarity_score * 100)

  return (
    <div
      className={`bg-white rounded-lg border-2 transition-all duration-200 cursor-pointer overflow-hidden hover:shadow-lg ${
        isSelected
          ? 'border-primary-500 shadow-lg'
          : 'border-gray-200 hover:border-primary-300'
      }`}
      onClick={() => onSelect?.(product.product_id)}
    >
      {/* Product Image */}
      <div className="relative w-full aspect-square bg-gray-100 overflow-hidden">
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.title}
            fill
            className="object-cover hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
            <span className="text-gray-400 text-sm">No image</span>
          </div>
        )}

        {/* Match Score Badge */}
        <div className="absolute top-2 right-2 bg-primary-600 text-white px-3 py-1 rounded-full text-xs font-bold">
          {matchPercentage}% Match
        </div>

        {/* Availability Badge */}
        {!product.availability && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <div className="bg-red-600 text-white px-3 py-1 rounded-lg font-semibold">
              Out of Stock
            </div>
          </div>
        )}

        {/* Favorite Button */}
        <button className="absolute top-2 left-2 p-2 bg-white rounded-full shadow-md hover:bg-gray-100 transition-colors duration-200">
          <HeartIcon className="h-5 w-5 text-gray-400 hover:text-red-500" />
        </button>
      </div>

      {/* Product Info */}
      <div className="p-4 space-y-3">
        {/* Title */}
        <div>
          <h3 className="font-semibold text-gray-900 line-clamp-2 text-sm">
            {product.title}
          </h3>
        </div>

        {/* Price */}
        <div className="space-y-1">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-primary-600">
              ${product.price.toFixed(2)}
            </span>
            <span className="text-xs text-gray-600">{product.currency}</span>
          </div>
        </div>

        {/* Rating */}
        {product.rating !== undefined && (
          <div className="flex items-center gap-1">
            <div className="flex items-center gap-0.5">
              {[...Array(5)].map((_, i) => (
                <StarIcon
                  key={i}
                  className={`h-3.5 w-3.5 ${
                    i < Math.floor(product.rating || 0)
                      ? 'text-yellow-400'
                      : 'text-gray-300'
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-gray-600">
              {product.rating?.toFixed(1)} ({product.reviews_count} reviews)
            </span>
          </div>
        )}

        {/* Store and Distance */}
        <div className="space-y-2 pt-2 border-t border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-semibold text-gray-700">🏪</span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {product.store_name}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <MapPinIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span className="text-xs text-gray-600">
              {product.distance_km < 1
                ? `${(product.distance_km * 1000).toFixed(0)}m away`
                : `${product.distance_km.toFixed(1)}km away`}
            </span>
          </div>
        </div>

        {/* Specs */}
        {product.specs && Object.keys(product.specs).length > 0 && (
          <div className="pt-2 border-t border-gray-200">
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(product.specs).slice(0, 2).map(([key, value]) => (
                <div key={key} className="text-xs">
                  <p className="text-gray-500 capitalize">{key}</p>
                  <p className="text-gray-900 font-medium">{value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Button */}
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="w-full mt-4 py-2 px-3 bg-primary-100 text-primary-700 rounded-lg font-medium text-sm hover:bg-primary-200 transition-colors duration-200 flex items-center justify-center gap-2"
        >
          View Product
          <ArrowTopRightOnSquareIcon className="h-4 w-4" />
        </a>
      </div>
    </div>
  )
}
