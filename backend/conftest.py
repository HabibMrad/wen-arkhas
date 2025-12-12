"""Pytest configuration and fixtures"""

import pytest
import os
import sys

# Add backend app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))


@pytest.fixture
def sample_location():
    """Sample location in Beirut"""
    return {"lat": 33.8886, "lng": 35.4955}


@pytest.fixture
def sample_stores():
    """Sample store data"""
    return [
        {
            "store_id": "store_1",
            "name": "Shoe Store 1",
            "address": "Beirut",
            "lat": 33.8886,
            "lng": 35.4955,
            "distance_km": 0.5,
            "website": "https://store1.com",
            "rating": 4.5,
        },
        {
            "store_id": "store_2",
            "name": "Shoe Store 2",
            "address": "Beirut",
            "lat": 33.8900,
            "lng": 35.4970,
            "distance_km": 1.2,
            "website": "https://store2.com",
            "rating": 4.2,
        },
    ]


@pytest.fixture
def sample_products():
    """Sample product data"""
    return [
        {
            "product_id": "prod_1",
            "store_id": "store_1",
            "title": "Adidas Samba OG",
            "price": 120.0,
            "currency": "USD",
            "rating": 4.8,
            "reviews_count": 45,
            "availability": True,
            "url": "https://store1.com/product/1",
            "specs": {"color": "black", "size": "42"},
        },
        {
            "product_id": "prod_2",
            "store_id": "store_2",
            "title": "Adidas Samba Classic",
            "price": 115.0,
            "currency": "USD",
            "rating": 4.6,
            "reviews_count": 38,
            "availability": True,
            "url": "https://store2.com/product/2",
            "specs": {"color": "white", "size": "42"},
        },
    ]


@pytest.fixture
def sample_query():
    """Sample search query"""
    return "adidas samba man 42 black"
