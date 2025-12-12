import math
import logging
from typing import Tuple, Dict, Optional
from app.config import settings
from app.models.schemas import LocationModel

logger = logging.getLogger(__name__)


class LocationService:
    """
    Service for location-based operations including distance calculation,
    geocoding, and location validation.
    """

    @staticmethod
    def calculate_distance(
        point1: Dict[str, float],
        point2: Dict[str, float]
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.
        Returns distance in kilometers.

        Args:
            point1: Dictionary with 'lat' and 'lng' keys
            point2: Dictionary with 'lat' and 'lng' keys

        Returns:
            Distance in kilometers
        """
        lat1 = point1.get("lat", 0)
        lng1 = point1.get("lng", 0)
        lat2 = point2.get("lat", 0)
        lng2 = point2.get("lng", 0)

        # Earth's radius in kilometers
        R = 6371.0

        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        distance = R * c

        return round(distance, 2)

    @staticmethod
    def validate_location(lat: float, lng: float) -> bool:
        """
        Validate if location is within Lebanon bounds.

        Lebanon bounds:
        - Latitude: 33.0 to 34.7
        - Longitude: 35.1 to 36.6

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate

        Returns:
            True if location is in Lebanon, False otherwise
        """
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            logger.warning(f"Invalid location type: lat={type(lat)}, lng={type(lng)}")
            return False

        is_valid = (
            settings.min_latitude <= lat <= settings.max_latitude
            and settings.min_longitude <= lng <= settings.max_longitude
        )

        if not is_valid:
            logger.warning(
                f"Location out of bounds: lat={lat}, lng={lng}. "
                f"Expected: lat [{settings.min_latitude}, {settings.max_latitude}], "
                f"lng [{settings.min_longitude}, {settings.max_longitude}]"
            )

        return is_valid

    @staticmethod
    def get_search_radius(
        center: Dict[str, float],
        radius_km: float = None
    ) -> Dict[str, float]:
        """
        Calculate bounding box for a search radius.
        Used for Google Places API queries.

        Args:
            center: Center point with 'lat' and 'lng'
            radius_km: Search radius in kilometers

        Returns:
            Dictionary with 'northeast' and 'southwest' corners
        """
        if radius_km is None:
            radius_km = settings.store_search_radius_km

        # Approximate degrees per km
        lat_offset = radius_km / 111.0  # ~111 km per degree latitude
        lng_offset = radius_km / (111.0 * math.cos(math.radians(center["lat"])))

        return {
            "northeast": {
                "lat": center["lat"] + lat_offset,
                "lng": center["lng"] + lng_offset,
            },
            "southwest": {
                "lat": center["lat"] - lat_offset,
                "lng": center["lng"] - lng_offset,
            },
        }

    @staticmethod
    def reverse_geocode(lat: float, lng: float) -> Optional[str]:
        """
        Reverse geocode coordinates to address (placeholder).
        Integration with Google Maps API will be added in Phase 3.

        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate

        Returns:
            Address string or None
        """
        logger.info(f"Reverse geocoding: lat={lat}, lng={lng}")
        # TODO: Implement with Google Maps API
        # For now, return formatted coordinates
        return f"{lat:.4f}, {lng:.4f}"

    @staticmethod
    def is_within_radius(
        point: Dict[str, float],
        center: Dict[str, float],
        radius_km: float = None
    ) -> bool:
        """
        Check if a point is within a radius of center.

        Args:
            point: Point to check
            center: Center point
            radius_km: Radius in kilometers

        Returns:
            True if point is within radius
        """
        if radius_km is None:
            radius_km = settings.store_search_radius_km

        distance = LocationService.calculate_distance(point, center)
        return distance <= radius_km

    @staticmethod
    def get_city_bounds(city_name: str = "beirut") -> Optional[Dict[str, float]]:
        """
        Get predefined bounds for Lebanese cities.

        Args:
            city_name: City name (lowercase)

        Returns:
            Dictionary with 'center' coordinates or None
        """
        cities = {
            "beirut": {
                "center": {"lat": 33.8886, "lng": 35.4955},
                "radius": 15,  # km
            },
            "tripoli": {
                "center": {"lat": 34.4325, "lng": 35.8455},
                "radius": 10,
            },
            "sidon": {
                "center": {"lat": 33.5597, "lng": 35.3724},
                "radius": 8,
            },
            "tyre": {
                "center": {"lat": 33.2732, "lng": 35.1988},
                "radius": 8,
            },
        }

        city = cities.get(city_name.lower())
        if city is None:
            logger.warning(f"Unknown city: {city_name}")
            return None

        return city

    @staticmethod
    def sort_by_distance(
        locations: list,
        center: Dict[str, float]
    ) -> list:
        """
        Sort locations by distance from center.

        Args:
            locations: List of location dicts with 'lat' and 'lng' keys
            center: Center point

        Returns:
            Sorted list of locations
        """
        def distance_key(loc):
            return LocationService.calculate_distance(center, loc)

        return sorted(locations, key=distance_key)
