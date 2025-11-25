"""
HTML generation functions for product display.
"""
import html
import ast
from typing import List, Dict


def generate_product_cards_html(products: List[Dict], user_query: str = "") -> str:
    """
    Generate beautiful product cards HTML
    """
    # Debug: print what we're receiving
    print(f"🎨 Generating HTML for {len(products)} products")
    for idx, p in enumerate(products):
        print(f"  Product {idx}: name='{p.get('product_name')}', price='{p.get('price')}'")
    
    # Use data attribute approach to avoid quote escaping issues
    if user_query:
        import json
        import html
        # JSON encode the query and HTML escape it for the data attribute
        user_query_json = json.dumps(user_query)
        user_query_escaped = html.escape(user_query_json)
        # Use data attribute and simple onclick that reads from data attribute
        notify_button = f'<button class="notify-button" data-query="{user_query_escaped}" onclick="handleNotifyClick(this)" style="margin-left: 20px; white-space: nowrap; cursor: pointer;">🔔 Notify Me on Price Drops</button>'
    else:
        notify_button = ''
    
    # Build header with notify button
    header_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h2 style="color: #2d3748; margin-bottom: 10px; margin: 0;">🎯 Best Deals Found</h2>
            <p style="color: #718096; margin: 5px 0 0 0;">Found {len(products)} products matching your search</p>
        </div>
        {notify_button}
    </div>
    """
    
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
        .notify-button {
            background: #48bb78;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 14px;
        }
        .notify-button:hover {
            background: #38a169;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #718096;
        }
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: white;
            margin: 15% auto;
            padding: 30px;
            border-radius: 12px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-header h2 {
            margin: 0;
            color: #2d3748;
        }
        .close {
            color: #aaa;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: #000;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #4a5568;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }
        .btn-primary {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .btn-secondary {
            background: #e2e8f0;
            color: #4a5568;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-secondary:hover {
            background: #cbd5e0;
        }
        .error-message {
            color: #e53e3e;
            font-size: 14px;
            margin-top: 8px;
        }
        .success-message {
            color: #48bb78;
            font-size: 14px;
            margin-top: 8px;
        }
    </style>
    """]
    
    # Add header with notify button
    html_parts.append(header_html)
    html_parts.append("""
    <div class="deals-container">
    """)
    
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
            
            <div style="margin-top: 12px;">
                <a href="{url}" target="_blank" class="product-link">
                    View Deal →
                </a>
            </div>
            
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

