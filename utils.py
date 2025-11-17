"""
Utility functions for DealFinder.
Helper functions for URL parsing, price extraction, and sorting.
"""
import re
from typing import List, Dict


def extract_domain(url: str) -> str:
    """Extract domain name from URL"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        # Remove www. prefix
        domain = domain.replace('www.', '')
        return domain
    except:
        return "Unknown"


def extract_price_value(price_str: str) -> float:
    """
    Extract numeric price value from price string for sorting.
    Returns float for comparison, or float('inf') if price not available.
    """
    if not price_str or price_str.lower() in ["price not available", "none", ""]:
        return float('inf')  # Put unavailable prices at the end
    
    # Remove currency symbols and extract numbers
    # Handle formats like: $999, $1,299.99, From $999, $999-$1,299
    price_str = price_str.replace('$', '').replace(',', '').strip()
    
    # Extract first number (for ranges like "$999-$1,299", take the lower price)
    price_match = re.search(r'(\d+\.?\d*)', price_str)
    if price_match:
        try:
            return float(price_match.group(1))
        except ValueError:
            return float('inf')
    
    return float('inf')


def sort_products_by_price(products: List[Dict]) -> List[Dict]:
    """
    Sort products by price (lowest first).
    Products without prices go to the end.
    """
    def get_sort_key(product: Dict) -> float:
        price = product.get("price", "")
        return extract_price_value(price)
    
    sorted_products = sorted(products, key=get_sort_key)
    
    # Log sorting info
    print(f"📊 Sorted {len(sorted_products)} products by price:")
    for idx, product in enumerate(sorted_products[:5], 1):  # Show top 5
        price = product.get("price", "Price not available")
        print(f"  {idx}. {product.get('product_name', 'Unknown')[:50]} - {price}")
    
    return sorted_products


def extract_text_from_agent_result(agent_result) -> str:
    """Helper to extract text from Strands AgentResult - simplifies response handling"""
    if hasattr(agent_result, 'message') and agent_result.message:
        if hasattr(agent_result.message, 'content'):
            content = agent_result.message.content
            if isinstance(content, list) and len(content) > 0:
                return content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
            return str(content)
        return str(agent_result.message)
    elif isinstance(agent_result, dict):
        msg = agent_result.get("message", {})
        if isinstance(msg, dict) and "content" in msg:
            content = msg["content"]
            if isinstance(content, list) and len(content) > 0:
                return content[0].get("text", "")
        return str(agent_result)
    return str(agent_result)

