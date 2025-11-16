import html
from typing import Optional
import os
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from strands import Agent
from strands.session import session_manager
from strands_tools import swarm
from strands_tools.tavily import (
    tavily_search, tavily_extract, tavily_crawl, tavily_map
)
from strands.models.openai import OpenAIModel
from pydantic import BaseModel
from guardrails import SimpleGuardrails, RateLimiter


app = FastAPI()

# Initialize guardrails
guardrails = SimpleGuardrails()
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)  # 20 requests per minute

html_page = """
<!DOCTYPE html>
<html>
<head>
    <title>DealFinder - Find Best Deals</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 48px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .header p {
            font-size: 18px;
            opacity: 0.9;
        }
        .search-box {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        .search-form {
            display: flex;
            gap: 10px;
        }
        .search-input {
            flex: 1;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s;
        }
        .search-input:focus {
            border-color: #667eea;
        }
        .search-button {
            padding: 15px 40px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        .search-button:hover {
            background: #5568d3;
        }
        .search-button:active {
            transform: scale(0.98);
        }
        .results-container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            min-height: 200px;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            border: 4px solid #f3f4f6;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .examples {
            margin-top: 20px;
            text-align: center;
        }
        .examples span {
            display: inline-block;
            background: #edf2f7;
            padding: 6px 12px;
            margin: 4px;
            border-radius: 6px;
            font-size: 14px;
            color: #4a5568;
            cursor: pointer;
            transition: background 0.2s;
        }
        .examples span:hover {
            background: #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛍️ DealFinder</h1>
            <p>Find the best deals on products you love</p>
        </div>
        
        <div class="search-box">
            <form method="post" action="/swarm" class="search-form" id="searchForm">
                <input type="text" name="msg" class="search-input" 
                       placeholder="Search for deals... (e.g., 'iPhone 15 deals', 'gaming laptop under $1000')"
                       required/>
                <button type="submit" class="search-button">🔍 Find Deals</button>
            </form>
            
            <div class="examples">
                <strong>Try:</strong>
                <span onclick="setQuery('laptop deals')">laptop deals</span>
                <span onclick="setQuery('iPhone 15 price')">iPhone 15 price</span>
                <span onclick="setQuery('gaming console under $400')">gaming console under $400</span>
                <span onclick="setQuery('MacBook Air M2 discount')">MacBook Air M2 discount</span>
            </div>
        </div>
        
        <div class="results-container">
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Finding the best deals for you...</p>
            </div>
            <div id="results">{{response}}</div>
        </div>
    </div>
    
    <script>
        function setQuery(query) {
            document.querySelector('.search-input').value = query;
        }
        
        document.getElementById('searchForm').addEventListener('submit', function() {
            document.getElementById('loading').classList.add('active');
            document.getElementById('results').style.display = 'none';
        });
    </script>
</body>
</html>
"""

class InputModel(BaseModel):
    input: str

@app.get("/", response_class=HTMLResponse)
def ui_home():
    return html_page.replace("{{response}}", "")

@app.post("/swarm", response_class=HTMLResponse)
async def swarm(request: Request):
    form = await request.form()
    user_input = form["msg"]

    # Get client IP for rate limiting
    client_ip = request.client.host

    # 1. Rate limiting check
    rate_allowed, rate_msg = rate_limiter.is_allowed(client_ip)
    if not rate_allowed:
        error_html = f"<div style='color: red;'><strong>⚠️ {rate_msg}</strong></div>"
        return html_page.replace("{{response}}", error_html)

    # 2. Input validation and safety check
    is_safe, safety_msg = guardrails.check_input(user_input)
    if not is_safe:
        error_html = f"<div style='color: red;'><strong>🚫 Input blocked:</strong> {safety_msg}</div>"
        return html_page.replace("{{response}}", error_html)

    # 3. Check if query is deal-related
    is_deal, deal_msg = guardrails.is_deal_related(user_input)
    if not is_deal:
        error_html = f"""
        <div style='color: orange; padding: 15px; border-left: 4px solid orange;'>
            <strong>🛒 Not a deal query</strong>
            <p>{deal_msg}</p>
            <p><strong>Examples:</strong></p>
            <ul>
                <li>"Find laptop deals"</li>
                <li>"iPhone 15 best price"</li>
                <li>"Cheap gaming console"</li>
                <li>"MacBook Air discount"</li>
            </ul>
        </div>
        """
        return html_page.replace("{{response}}", error_html)
    
    # 4. Sanitize input

    sanitized_input = guardrails.sanitize_for_deals(user_input)
    print(f"Processing query: {sanitized_input}")

    try:
        model = OpenAIModel(
            client_args={
                "api_key": os.getenv("OPENAI_API_KEY"),
            },
            model_id="gpt-4o-mini",  # Specify the model name here
            params={
                "max_tokens": 1000,
                "temperature": 0.7
            }
        )
        agent = Agent(model=model,
                      tools=[swarm, tavily_search, tavily_extract, tavily_crawl],
                      system_prompt="You are a deal finding assistant, find best deals for the user based on their query"
                      )
        # Real-time web search to get URLs
        result = agent.tool.tavily_search(
            query=sanitized_input,
            search_depth="advanced",
            topic="general",
            max_results=10,
            include_raw_content=False  # Don't need raw content yet
        )
        
        # Extract and parse product details from results
        html_output = extract_and_display_products(
            result, 
            sanitized_input, 
            model
        )
        
        # Check output safety (optional)
        # output_safe, output_msg = guardrails.check_output(html_output)
        # if not output_safe:
        #     return html_page.replace("{{response}}", 
        #         f"<div style='color: orange;'>⚠️ Response filtered for safety</div>")
        
        return html_page.replace("{{response}}", html_output)

    except Exception as e:
        print(f"Error processing request: {e}")
        error_html = f"<div style='color: red;'>❌ An error occurred. Please try again.</div>"
        return html_page.replace("{{response}}", error_html)



import json
import ast
import re
from typing import List, Dict


def extract_and_display_products(result_dict, user_query: str, model) -> str:
    """
    Extract product details using tavily_extract for full page content
    """
    try:
        # Extract "text" field inside content[0]
        text_block = result_dict["content"][0]["text"]
        
        # Try to parse as JSON/dict
        try:
            inner_data = ast.literal_eval(text_block)
        except (ValueError, SyntaxError) as e:
            print(f"Error parsing search results: {e}")
            print(f"Text block: {text_block[:200]}")
            # Try JSON parse as fallback
            try:
                inner_data = json.loads(text_block)
            except:
                return "<div style='color: red;'>Error parsing search results. Please try again.</div>"
        
        results = inner_data.get("results", [])
        
        if not results:
            return "<div style='color: orange;'>No results found. Try a different search.</div>"
        
        # Parse products using tavily_extract
        products = parse_products_with_extract(results, user_query, model)
        
        # Generate HTML
        return generate_product_cards_html(products)
        
    except Exception as e:
        print(f"Error extracting products: {e}")
        # Fallback to simple display
        return convert_agent_json_to_html_simple(result_dict)


def parse_products_with_extract(results: List[Dict], user_query: str, model) -> List[Dict]:
    """
    Use tavily_extract to get full page content, then LLM to parse product details
    """
    products = []
    
    for idx, result in enumerate(results[:3]):  # Only top 3 due to cost/speed
        try:
            title = result.get("title", "")
            url = result.get("url", "")
            
            print(f"Extracting full content from: {url}")
            
            # Use tavily_extract to get full page content
            try:
                extract_result = tavily_extract(url=url)
                
                # Extract the content from the result
                if isinstance(extract_result, dict):
                    full_content = extract_result.get("content", "")
                elif hasattr(extract_result, 'content'):
                    # Handle if it's an object with content attribute
                    content_data = extract_result.content
                    if isinstance(content_data, list) and len(content_data) > 0:
                        full_content = content_data[0].get("text", "")
                    else:
                        full_content = str(content_data)
                else:
                    full_content = str(extract_result)
                
                if not full_content or full_content == "":
                    print(f"No content extracted for {url}, using title only")
                    products.append({
                        "product_name": title,
                        "details": "",
                        "price": "Price not available",
                        "deal_info": "",
                        "url": url,
                        "source": extract_domain(url)
                    })
                    continue
                
            except Exception as e:
                print(f"Error extracting content from {url}: {e}")
                # Fallback to basic info
                products.append({
                    "product_name": title,
                    "details": "",
                    "price": "Price not available",
                    "deal_info": "",
                    "url": url,
                    "source": extract_domain(url)
                })
                continue
            
            # Truncate content to avoid token limits (but use more than snippets)
            content_excerpt = full_content[:4000]  # 2x the snippet length
            
            # Use LLM to extract product details from full content
            prompt = f"""Extract product information from this webpage for the query: "{user_query}"

Page Title: {title}
URL: {url}
Page Content: {content_excerpt}

Extract and return ONLY a JSON object with these fields:
{{
  "product_name": "Specific product name with model (e.g., 'MacBook Air M2 13-inch')",
  "details": "Model, color, storage, configuration (e.g., '256GB, Space Gray, 8GB RAM')",
  "price": "Current price with currency (e.g., '$999' or 'From $999')",
  "deal_info": "Discount, savings, or promotion (e.g., 'Save $200' or '20% off' or 'Black Friday Deal')",
  "in_stock": true/false
}}

Be specific and accurate. Extract actual prices and deal information from the content.
If information is not available, use empty string for text fields.
Return ONLY valid JSON, no other text."""

            response = model.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower temp for more consistent extraction
                max_tokens=400
            )
            
            # Parse LLM response
            llm_output = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            llm_output = re.sub(r'```json\s*', '', llm_output)
            llm_output = re.sub(r'```\s*', '', llm_output)
            
            product_data = json.loads(llm_output)
            
            # Add URL and source
            product_data["url"] = url
            product_data["source"] = extract_domain(url)
            
            products.append(product_data)
            print(f"✅ Extracted: {product_data.get('product_name')} - {product_data.get('price')}")
            
        except Exception as e:
            print(f"Error parsing result {idx}: {e}")
            # Fallback to basic info
            products.append({
                "product_name": result.get("title", "Product"),
                "details": "",
                "price": "Price not available",
                "deal_info": "",
                "url": result.get("url", "#"),
                "source": extract_domain(result.get("url", ""))
            })
    
    return products


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


def generate_product_cards_html(products: List[Dict]) -> str:
    """
    Generate beautiful product cards HTML
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
        product_name = html.escape(product.get("product_name", "Product"))
        details = html.escape(product.get("details", ""))
        price = html.escape(product.get("price", "Price not available"))
        deal_info = html.escape(product.get("deal_info", ""))
        url = product.get("url", "#")
        source = html.escape(product.get("source", ""))
        
        # Build product card
        card_html = f"""
        <div class="product-card">
            <div class="product-name">{product_name}</div>
            {f'<div class="product-details">{details}</div>' if details else ''}
            
            <div class="price-section">
                <div class="product-price">{price}</div>
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
