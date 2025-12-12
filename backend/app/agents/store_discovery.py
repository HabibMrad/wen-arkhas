import logging
import time
from typing import Dict, Any, List, Optional
import googlemaps
from app.config import settings
from app.services.location import LocationService
from app.services.cache import CacheManager
from app.models.schemas import SearchState, StoreModel

logger = logging.getLogger(__name__)


class StoreDiscoveryAgent:
    """
    LangGraph Agent Node: Discovers nearby stores using Google Places API.

    Responsibilities:
    - Find stores near user location
    - Filter by rating, hours, and category
    - Cache results for 24 hours
    - Sort by distance

    Input: SearchState with 'location' and 'parsed_query'
    Output: SearchState with 'stores' field populated
    """

    # Store category keywords mapping
    CATEGORY_KEYWORDS = {
        "shoes": ["shoe", "footwear", "sports shoe", "sneaker"],
        "clothing": ["clothing", "apparel", "fashion", "garment"],
        "electronics": ["electronics", "mobile", "phone", "computer"],
        "accessories": ["accessories", "bag", "jewelry", "watch"],
    }

    def __init__(self, gmaps_client: Optional[googlemaps.Client] = None):
        """
        Initialize StoreDiscoveryAgent.

        Args:
            gmaps_client: Google Maps client (creates new if None)
        """
        if gmaps_client:
            self.gmaps = gmaps_client
        else:
            try:
                self.gmaps = googlemaps.Client(
                    key=settings.google_places_api_key,
                    timeout=30
                )
                logger.info("Google Maps client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Maps client: {str(e)}")
                self.gmaps = None

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Discover stores near user location.

        Args:
            state: SearchState dict with 'location' and 'parsed_query'

        Returns:
            Updated state with 'stores' field
        """
        start_time = time.time()
        logger.info("StoreDiscoveryAgent starting")

        try:
            # Get location
            location = state.get("location", {})
            if not location.get("lat") or not location.get("lng"):
                error_msg = "Location coordinates missing"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                return state

            # Validate location
            if not LocationService.validate_location(location["lat"], location["lng"]):
                error_msg = "Invalid location (outside Lebanon)"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                return state

            # Get search category
            category = self._get_search_category(state)
            logger.debug(f"Search category: {category}")

            # Check cache
            cache_key = CacheManager.generate_key(
                "stores",
                str(location["lat"]),
                str(location["lng"]),
                category
            )

            cache = CacheManager()
            cached_stores = await cache.get_stores(cache_key)
            if cached_stores:
                logger.info(f"Cache hit: {len(cached_stores)} stores found")
                state["stores"] = [StoreModel(**store) for store in cached_stores]
                state["execution_time_ms"]["discover_stores"] = int(
                    (time.time() - start_time) * 1000
                )
                return state

            # Discover stores via API
            if self.gmaps is None:
                error_msg = "Google Maps API not available"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                return state

            stores = await self._discover_stores(location, category)

            if not stores:
                logger.warning(f"No stores found for category: {category}")
                state["stores"] = []
            else:
                logger.info(f"Found {len(stores)} stores")
                # Sort by distance
                sorted_stores = LocationService.sort_by_distance(
                    [{"lat": s.lat, "lng": s.lng, **s.dict()} for s in stores],
                    location
                )
                state["stores"] = [StoreModel(**store) for store in sorted_stores]

                # Cache results (24h)
                store_dicts = [store.dict(exclude_unset=True) for store in state["stores"]]
                await cache.set_stores(cache_key, store_dicts, ttl_hours=24)

            # Track execution time
            state["execution_time_ms"]["discover_stores"] = int(
                (time.time() - start_time) * 1000
            )

            logger.info(f"StoreDiscoveryAgent completed in "
                       f"{state['execution_time_ms']['discover_stores']}ms")

            return state

        except Exception as e:
            error_msg = f"StoreDiscoveryAgent error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            state["errors"].append(error_msg)
            return state

    async def _discover_stores(
        self,
        location: Dict[str, float],
        category: str
    ) -> List[StoreModel]:
        """
        Discover stores using Google Places API.

        Args:
            location: User location {lat, lng}
            category: Product category for search

        Returns:
            List of StoreModel objects
        """
        try:
            # Get search radius
            search_radius = settings.store_search_radius_km * 1000  # Convert to meters

            # Build search query
            search_query = self._build_search_query(category)
            logger.debug(f"Search query: {search_query}")

            # Search nearby places
            places_result = self.gmaps.places_nearby(
                location=(location["lat"], location["lng"]),
                radius=search_radius,
                keyword=search_query,
                type="store"
            )

            stores = []
            for place in places_result.get("results", []):
                try:
                    store = self._parse_place_result(place, location)
                    if store and self._is_valid_store(store):
                        stores.append(store)
                except Exception as e:
                    logger.warning(f"Error parsing place: {str(e)}")
                    continue

            # Handle pagination
            next_page_token = places_result.get("next_page_token")
            if next_page_token and len(stores) < settings.max_stores_per_search:
                try:
                    time.sleep(2)  # Rate limiting
                    next_result = self.gmaps.places_nearby(
                        page_token=next_page_token
                    )
                    for place in next_result.get("results", []):
                        store = self._parse_place_result(place, location)
                        if store and self._is_valid_store(store):
                            stores.append(store)
                except Exception as e:
                    logger.warning(f"Error on next page: {str(e)}")

            # Limit results
            return stores[:settings.max_stores_per_search]

        except Exception as e:
            logger.error(f"Error discovering stores: {str(e)}")
            return []

    def _parse_place_result(
        self,
        place: Dict[str, Any],
        user_location: Dict[str, float]
    ) -> Optional[StoreModel]:
        """
        Parse Google Places result into StoreModel.

        Args:
            place: Google Places API result
            user_location: User's location for distance calculation

        Returns:
            StoreModel or None if parsing fails
        """
        try:
            place_id = place.get("place_id")
            name = place.get("name")
            location = place.get("geometry", {}).get("location", {})
            rating = place.get("rating", 0.0)
            is_open = place.get("opening_hours", {}).get("open_now", True)

            if not place_id or not name or not location:
                return None

            lat = location.get("lat")
            lng = location.get("lng")

            if not lat or not lng:
                return None

            # Calculate distance
            distance = LocationService.calculate_distance(
                user_location,
                {"lat": lat, "lng": lng}
            )

            # Create StoreModel
            store = StoreModel(
                store_id=place_id,
                name=name,
                address=place.get("vicinity", ""),
                lat=lat,
                lng=lng,
                distance_km=distance,
                website=None,  # Would need place details API
                phone=None,    # Would need place details API
                rating=rating,
                reviews_count=place.get("user_ratings_total", 0),
                currently_open=is_open
            )

            return store

        except Exception as e:
            logger.warning(f"Error parsing place result: {str(e)}")
            return None

    def _is_valid_store(self, store: StoreModel) -> bool:
        """
        Validate store meets criteria.

        Args:
            store: StoreModel to validate

        Returns:
            True if store meets filters
        """
        # Check minimum rating
        if store.rating < settings.min_store_rating:
            logger.debug(f"Store {store.name} filtered (rating {store.rating})")
            return False

        # Check distance
        if store.distance_km > settings.store_search_radius_km:
            logger.debug(f"Store {store.name} filtered (distance {store.distance_km}km)")
            return False

        return True

    def _build_search_query(self, category: str) -> str:
        """
        Build search query for Google Places.

        Args:
            category: Product category

        Returns:
            Search query string
        """
        keywords = self.CATEGORY_KEYWORDS.get(category, [])
        if not keywords:
            return "store retail"

        # Use primary keyword
        return keywords[0]

    def _get_search_category(self, state: Dict[str, Any]) -> str:
        """
        Get search category from parsed query.

        Args:
            state: SearchState dict

        Returns:
            Category string
        """
        parsed = state.get("parsed_query")
        if parsed and parsed.category:
            return parsed.category

        # Fallback to generic
        return "general"


# Define the async node function for LangGraph
async def discover_stores_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node function for store discovery.

    Args:
        state: Current workflow state

    Returns:
        Updated state with stores
    """
    agent = StoreDiscoveryAgent()
    return await agent.execute(state)
