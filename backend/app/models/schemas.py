from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class LocationModel(BaseModel):
    latitude: float
    longitude: float


class SearchRequest(BaseModel):
    query: str = Field(..., description="User product search query")
    location: LocationModel = Field(..., description="User location for price comparison")



class Currency(str, Enum):
    """Supported currencies"""
    USD = "USD"
    LBP = "LBP"


class LocationModel(BaseModel):
    """Location representation"""
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    address: Optional[str] = Field(None, description="Human-readable address")


class ParsedQuery(BaseModel):
    """Structured product query"""
    brand: Optional[str] = Field(None, description="Product brand")
    model: Optional[str] = Field(None, description="Product model/name")
    category: Optional[str] = Field(None, description="Product category")
    size: Optional[str] = Field(None, description="Product size")
    gender: Optional[str] = Field(None, description="Product gender (M/F/Unisex)")
    color: Optional[str] = Field(None, description="Product color")
    details: Optional[str] = Field(None, description="Additional product details")
    original_query: str = Field(..., description="Original search query")


class StoreModel(BaseModel):
    """Store information"""
    store_id: str = Field(..., description="Unique store identifier")
    name: str = Field(..., description="Store name")
    address: str = Field(..., description="Store address")
    lat: float = Field(..., description="Store latitude")
    lng: float = Field(..., description="Store longitude")
    distance_km: float = Field(..., description="Distance from user location")
    website: Optional[str] = Field(None, description="Store website URL")
    phone: Optional[str] = Field(None, description="Store phone number")
    rating: float = Field(0.0, ge=0.0, le=5.0, description="Store rating 0-5")
    reviews_count: int = Field(0, ge=0, description="Number of reviews")
    currently_open: bool = Field(True, description="Is store currently open")
    hours: Optional[Dict[str, str]] = Field(None, description="Store opening hours")


class ProductModel(BaseModel):
    """Product information"""
    product_id: str = Field(..., description="Unique product identifier")
    store_id: str = Field(..., description="Store ID where product is found")
    title: str = Field(..., description="Product title")
    price: float = Field(..., ge=0, description="Product price")
    currency: Currency = Field(default=Currency.USD, description="Price currency")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Product rating")
    reviews_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    availability: bool = Field(True, description="Is product in stock")
    url: str = Field(..., description="Product URL")
    image_url: Optional[str] = Field(None, description="Product image URL")
    specs: Optional[Dict[str, str]] = Field(None, description="Product specifications")
    description: Optional[str] = Field(None, description="Product description")


class MatchedProduct(ProductModel):
    """Product with semantic matching score"""
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Semantic similarity to query")
    store_name: str = Field(..., description="Associated store name")
    distance_km: float = Field(..., description="Distance to store")


class Recommendation(BaseModel):
    """Product recommendation"""
    rank: int = Field(..., ge=1, description="Recommendation rank")
    product_id: str = Field(..., description="Product ID")
    category: str = Field(..., description="Recommendation category (best_value, best_rating, closest)")
    pros: List[str] = Field(default_factory=list, description="Advantages")
    cons: List[str] = Field(default_factory=list, description="Disadvantages")
    reasoning: Optional[str] = Field(None, description="Why this product is recommended")


class PriceAnalysis(BaseModel):
    """Price analysis data"""
    min_price: float = Field(..., ge=0, description="Minimum price found")
    max_price: float = Field(..., ge=0, description="Maximum price found")
    average_price: float = Field(..., ge=0, description="Average price")
    median_price: float = Field(..., ge=0, description="Median price")
    currency: Currency = Field(default=Currency.USD)


class AnalysisResult(BaseModel):
    """LLM analysis output"""
    best_value: Optional[Dict] = Field(None, description="Best value product recommendation")
    top_3_recommendations: List[Recommendation] = Field(default_factory=list)
    price_analysis: Optional[PriceAnalysis] = Field(None)
    summary: Optional[str] = Field(None, description="2-3 sentence summary")


class SearchResponse(BaseModel):
    """Complete search response"""
    search_id: str = Field(..., description="Unique search ID")
    query: str = Field(..., description="Original search query")
    location: LocationModel = Field(..., description="Search location")
    stores_found: int = Field(..., ge=0, description="Number of stores found")
    products_found: int = Field(..., ge=0, description="Number of products found")
    stores: List[StoreModel] = Field(default_factory=list, description="Nearby stores")
    results: List[MatchedProduct] = Field(default_factory=list, description="Matched products")
    analysis: Optional[AnalysisResult] = Field(None, description="LLM analysis")
    cached: bool = Field(False, description="Was result from cache")
    execution_time_ms: Optional[Dict[str, int]] = Field(None, description="Execution times per agent")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SearchState(BaseModel):
    """LangGraph workflow state"""
    query: str
    location: Dict[str, float]
    parsed_query: Optional[ParsedQuery] = None
    stores: List[StoreModel] = Field(default_factory=list)
    raw_products: List[ProductModel] = Field(default_factory=list)
    matched_products: List[MatchedProduct] = Field(default_factory=list)
    analysis: Optional[AnalysisResult] = None
    errors: List[str] = Field(default_factory=list)
    execution_time_ms: Dict[str, int] = Field(default_factory=dict)

from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str = Field(..., description="Product search query")
    location: LocationModel
