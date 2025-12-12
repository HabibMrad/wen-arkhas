import re
from typing import Dict, Optional
from app.models.schemas import ParsedQuery


class QueryParser:
    """
    Query parser that extracts structured product information.
    Supports brand, model, category, size, gender, color extraction.
    """

    # Brand mappings
    BRANDS = {
        "adidas": "Adidas",
        "nike": "Nike",
        "puma": "Puma",
        "reebok": "Reebok",
        "samsung": "Samsung",
        "apple": "Apple",
        "lg": "LG",
        "sony": "Sony",
    }

    # Category keywords
    CATEGORY_KEYWORDS = {
        "shoes": ["shoe", "sneaker", "boot", "sandal", "loafer"],
        "clothing": ["shirt", "pants", "dress", "jacket", "sweater", "coat"],
        "electronics": ["phone", "laptop", "tablet", "camera", "headphone"],
        "accessories": ["watch", "belt", "hat", "scarf", "bag", "glasses"],
    }

    # Gender keywords (order matters - check women before men)
    GENDER_KEYWORDS = {
        "women": ["women", "woman", "female", "girl"],
        "men": ["men", "man", "male", "boy"],
        "unisex": ["unisex", "all", "any"],
    }

    # Color keywords
    COLOR_KEYWORDS = ["black", "white", "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "gray", "grey"]

    # Size patterns
    SIZE_PATTERNS = {
        "shoes": r"\b(\d{1,2}(?:\.\d)?)\b",  # 42, 8, 10.5
        "clothing": r"\b([XS]{1,3}|M|L|XL+)\b",  # XS, S, M, L, XL, XXL
    }

    @staticmethod
    def parse(query: str) -> ParsedQuery:
        """Parse a query into structured components."""
        if not query:
            return ParsedQuery(
                brand=None,
                model=None,
                category=None,
                size=None,
                gender=None,
                color=None,
                details=None,
                original_query=""
            )

        q = query.strip().lower()
        parts = q.split()

        brand = QueryParser._extract_brand(query)
        category = QueryParser._extract_category(query)
        size = QueryParser._extract_size(query, category)
        gender = QueryParser._extract_gender(query)
        color = QueryParser._extract_color(query)

        # Extract model: words between brand and special attributes
        model = None
        if len(parts) > 1:
            # Get all parts that aren't brand, gender, color, or size
            model_parts = []
            for i, part in enumerate(parts):
                if i == 0:  # Skip brand (first word)
                    continue
                if part.lower() in ["size"]:
                    break
                # Skip if it's a known gender, color, or category keyword
                skip = False
                for gender_keywords in QueryParser.GENDER_KEYWORDS.values():
                    if part.lower() in gender_keywords:
                        skip = True
                        break
                if part.lower() in QueryParser.COLOR_KEYWORDS:
                    skip = True

                if not skip and part.isalpha():
                    model_parts.append(part)

            model = " ".join(model_parts).title() if model_parts else (parts[1].title() if len(parts) > 1 else None)

        details = " ".join(parts[2:]) if len(parts) > 2 else None

        return ParsedQuery(
            brand=brand,
            model=model,
            category=category,
            size=size,
            gender=gender,
            color=color,
            details=details,
            original_query=query
        )

    @staticmethod
    def _extract_brand(query: str) -> Optional[str]:
        """Extract brand from query."""
        q_lower = query.lower()
        for brand_key, brand_name in QueryParser.BRANDS.items():
            if brand_key in q_lower:
                return brand_name
        return None

    @staticmethod
    def _extract_category(query: str) -> Optional[str]:
        """Extract category from query."""
        q_lower = query.lower()
        for category, keywords in QueryParser.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in q_lower:
                    return category
        return None

    @staticmethod
    def _extract_gender(query: str) -> Optional[str]:
        """Extract gender from query."""
        q_lower = query.lower()
        for gender, keywords in QueryParser.GENDER_KEYWORDS.items():
            for keyword in keywords:
                if keyword in q_lower:
                    return gender
        return None

    @staticmethod
    def _extract_color(query: str) -> Optional[str]:
        """Extract color from query."""
        q_lower = query.lower()
        for color in QueryParser.COLOR_KEYWORDS:
            if color in q_lower:
                return color
        return None

    @staticmethod
    def _extract_size(query: str, category: Optional[str] = None) -> Optional[str]:
        """Extract size from query based on category or general pattern."""
        q_lower = query.lower()

        # Try category-specific patterns first
        if category:
            pattern = QueryParser.SIZE_PATTERNS.get(category)
            if pattern:
                match = re.search(pattern, q_lower, re.IGNORECASE)
                if match:
                    return match.group(1)

        # Try general number pattern for size-like numbers
        # Look for numbers that appear after "size" or standalone
        match = re.search(r'(?:size\s+)?(\d{1,2}(?:\.\d)?)', q_lower)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def get_fallback_category(query: str) -> str:
        """Get fallback category if not detected."""
        category = QueryParser._extract_category(query)
        return category if category else "general"

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize whitespace and lowercase."""
        return " ".join(query.lower().split())

    @staticmethod
    def build_search_terms(parsed: ParsedQuery) -> str:
        """
        Combines parsed parts into a search term.
        """
        terms = []

        if parsed.brand:
            terms.append(parsed.brand)

        if parsed.model:
            terms.append(parsed.model)

        if parsed.color:
            terms.append(parsed.color)

        if parsed.size:
            terms.append(parsed.size)

        # If nothing extracted, use original
        return " ".join(terms) if terms else parsed.original_query
