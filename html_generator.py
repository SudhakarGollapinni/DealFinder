"""
HTML generation functions for product display.
"""
import html
import ast
from typing import List, Dict


def generate_product_cards_html(products: List[Dict]) -> str:
    """
    Generate beautiful product cards HTML
    """
    # Debug: print what we're receiving
    print(f"🎨 Generating HTML for {len(products)} products")
    for idx, p in enumerate(products):
        print(f"  Product {idx}: name='{p.get('product_name')}', price='{p.get('price')}'")
    
    html_parts = ["""
    <style>
        .deals-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .product-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 16px;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .product-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .product-name {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
            line-height: 1.3;
        }
        .product-details {
            font-size: 14px;
            color: #666;
            margin-bottom: 12px;
            line-height: 1.4;
        }
        .price-section {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .product-price {
            font-size: 24px;
            font-weight: bold;
            color: #2c5282;
        }
        .deal-badge {
            background: #48bb78;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .product-link {
            display: inline-block;
            background: #3182ce;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.2s;
        }
        .product-link:hover {
            background: #2c5282;
        }
        .source-tag {
            display: inline-block;
            background: #edf2f7;
            color: #4a5568;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-top: 8px;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #718096;
        }
    </style>
    
    <h2 style="color: #2d3748; margin-bottom: 10px;">🎯 Best Deals Found</h2>
    <p style="color: #718096; margin-bottom: 20px;">Found {count} products matching your search</p>
    
    <div class="deals-container">
    """.replace("{count}", str(len(products)))]
    
    if not products:
        html_parts.append("""
        <div class="no-results">
            <h3>😕 No deals found</h3>
            <p>Try refining your search or check back later!</p>
        </div>
        """)
    
    for product in products:
        product_name = html.escape(str(product.get("product_name", "Product")))
        details = html.escape(str(product.get("details", "")))
        # Get price and ensure it's a string - be very explicit
        raw_price = product.get("price")
        print(f"  DEBUG: raw_price type={type(raw_price)}, value={repr(raw_price)}")
        
        if raw_price is None:
            price = "Price not available"
        elif isinstance(raw_price, str):
            price = html.escape(raw_price.strip()) if raw_price.strip() else "Price not available"
        else:
            price = html.escape(str(raw_price).strip()) if str(raw_price).strip() else "Price not available"
        
        deal_info = html.escape(str(product.get("deal_info", "")))
        url = product.get("url", "#")
        source = html.escape(str(product.get("source", "")))
        
        # Debug: print what we're rendering
        print(f"  ✅ Rendering product card:")
        print(f"     - Name: '{product_name}'")
        print(f"     - Price: '{price}' (raw was: {repr(raw_price)})")
        print(f"     - URL: '{url}'")
        
        # Build product card - ensure price is always visible
        card_html = f"""
        <div class="product-card">
            <div class="product-name">{product_name}</div>
            {f'<div class="product-details">{details}</div>' if details else ''}
            
            <div class="price-section">
                <div class="product-price" style="color: #2c5282; font-size: 24px; font-weight: bold;">{price}</div>
                {f'<div class="deal-badge">{deal_info}</div>' if deal_info else ''}
            </div>
            
            <a href="{url}" target="_blank" class="product-link">
                View Deal →
            </a>
            
            {f'<div class="source-tag">📍 {source}</div>' if source else ''}
        </div>
        """
        
        html_parts.append(card_html)
    
    html_parts.append("</div>")
    
    return "\n".join(html_parts)


def convert_agent_json_to_html_simple(result_dict):
    """
    Fallback: Simple display if product parsing fails
    """
    try:
        text_block = result_dict["content"][0]["text"]
        inner_data = ast.literal_eval(text_block)
        results = inner_data.get("results", [])
        
        html_parts = ["<h3>Search Results</h3>", "<ul>"]
        
        for r in results:
            title = html.escape(r.get("title", "No title"))
            url = r.get("url", "#")
            html_parts.append(
                f"<li><a href='{url}' target='_blank'>{title}</a></li>"
            )
        
        html_parts.append("</ul>")
        return "\n".join(html_parts)
    except:
        return "<div style='color: red;'>Error displaying results</div>"

