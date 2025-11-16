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
        #results {
            display: block !important;
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
            // Don't hide results - let the new page load show them
        });
        
        // Ensure results are visible when page loads
        window.addEventListener('load', function() {
            document.getElementById('loading').classList.remove('active');
            var resultsDiv = document.getElementById('results');
            if (resultsDiv) {
                resultsDiv.style.display = 'block';
                // Debug: log what's in the results div
                console.log('Results div content length:', resultsDiv.innerHTML.length);
                console.log('Results div has price elements:', resultsDiv.querySelectorAll('.product-price').length);
            }
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
        # Real-time web search to get URLs and snippets
        result = agent.tool.tavily_search(
            query=sanitized_input,
            search_depth="advanced",
            topic="general",
            max_results=10,
            include_raw_content=True  # Get snippets which may contain prices
        )
        
        # Extract and parse product details from results
        html_output = await extract_and_display_products(
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


async def extract_and_display_products(result_dict, user_query: str, model) -> str:
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
        products = await parse_products_with_extract(results, user_query, model)
        
        # Generate HTML
        return generate_product_cards_html(products)
        
    except Exception as e:
        print(f"Error extracting products: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to simple display
        return convert_agent_json_to_html_simple(result_dict)


async def parse_products_with_extract(results: List[Dict], user_query: str, model) -> List[Dict]:
    """
    Use tavily_extract to get full page content, then LLM to parse product details
    """
    products = []
    
    for idx, result in enumerate(results[:3]):  # Only top 3 due to cost/speed
        try:
            title = result.get("title", "")
            url = result.get("url", "")
            # Check if search result snippet already has a price
            snippet = result.get("content", "") or result.get("raw_content", "") or ""
            snippet_price = None
            product_name_from_snippet = None
            
            if snippet:
                # Try to extract price from snippet
                price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', snippet)
                if price_match:
                    snippet_price = price_match.group(0)
                    print(f"💰 Found price in search snippet: {snippet_price}")
                
                # Try to extract product name from snippet (first 100 chars usually have it)
                snippet_preview = snippet[:200]
                print(f"📄 Snippet preview: {snippet_preview}")
            
            # If snippet has price, use it directly without expensive extraction
            if snippet_price:
                print(f"✅ Using snippet price, skipping full extraction for speed")
                products.append({
                    "product_name": title,
                    "details": snippet[:150] if snippet else "",  # Use first part of snippet as details
                    "price": snippet_price,
                    "deal_info": "",
                    "url": url,
                    "source": extract_domain(url)
                })
                continue
            
            print(f"Extracting full content from: {url}")
            
            # Use tavily_extract to get full page content
            try:
                # tavily_extract expects a list of URLs and is async
                extract_result = await tavily_extract(urls=[url], extract_depth="advanced", format="text")
                
                # Parse the result structure
                # tavily_extract returns: {"status": "success", "content": [{"text": str(api_response)}]}
                if not isinstance(extract_result, dict):
                    raise ValueError(f"Unexpected extract_result type: {type(extract_result)}")
                
                if extract_result.get("status") != "success":
                    error_msg = extract_result.get("content", [{}])[0].get("text", "Unknown error")
                    print(f"Tavily extract failed for {url}: {error_msg}")
                    raise ValueError(f"Extraction failed: {error_msg}")
                
                # The content is a string representation of the API response
                content_list = extract_result.get("content", [])
                if not content_list or len(content_list) == 0:
                    raise ValueError("No content in extract result")
                
                # Parse the string representation of the API response
                api_response_str = content_list[0].get("text", "")
                if not api_response_str:
                    raise ValueError("Empty content text")
                
                print(f"🔍 Raw API response string (first 500 chars): {api_response_str[:500]}")
                
                # Try to parse the API response JSON
                try:
                    api_response = json.loads(api_response_str)
                except json.JSONDecodeError:
                    # If it's not JSON, try ast.literal_eval (for Python dict string representation)
                    try:
                        api_response = ast.literal_eval(api_response_str)
                    except Exception as e:
                        print(f"⚠️ Failed to parse API response as JSON or Python dict: {e}")
                        # If all else fails, use the string as-is
                        api_response = {"results": [{"raw_content": api_response_str}]}
                
                print(f"🔍 Parsed API response keys: {list(api_response.keys()) if isinstance(api_response, dict) else 'Not a dict'}")
                
                # Extract the actual content from the API response
                # Tavily extract API returns: {"results": [{"raw_content": "...", "url": "..."}]}
                if "results" in api_response and len(api_response["results"]) > 0:
                    # Find the result matching our URL
                    matching_result = None
                    for res in api_response["results"]:
                        if res.get("url") == url:
                            matching_result = res
                            break
                    # If no match, use first result
                    if not matching_result:
                        matching_result = api_response["results"][0]
                    
                    # Tavily uses "raw_content" not "content"
                    full_content = matching_result.get("raw_content", matching_result.get("content", ""))
                    content_length = len(full_content) if full_content else 0
                    print(f"✅ Extracted content length: {content_length}")
                    if content_length > 0:
                        # Show a sample to verify we got real content
                        sample = full_content[:200].replace('\n', ' ')
                        print(f"📄 Content sample: {sample}...")
                    else:
                        print(f"⚠️ WARNING: No content extracted! This might be why prices aren't showing.")
                elif "raw_content" in api_response:
                    full_content = api_response["raw_content"]
                elif "content" in api_response:
                    full_content = api_response["content"]
                else:
                    # Fallback: use the string representation
                    print(f"⚠️ No results or content found, using string as fallback")
                    full_content = api_response_str
                
                if not full_content or full_content == "" or full_content == "None":
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
                import traceback
                traceback.print_exc()
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
            
            # Debug: print first 500 chars of content to verify we're getting data
            print(f"Content preview (first 500 chars): {content_excerpt[:500]}")
            
            # Check if content contains price-like patterns
            price_patterns = re.findall(r'\$[\d,]+(?:\.\d{2})?', content_excerpt)
            if price_patterns:
                print(f"💰 Found {len(price_patterns)} price patterns in content: {price_patterns[:5]}")
            else:
                print(f"⚠️ No price patterns found in content (searching for $XXX format)")
            
            # Use LLM to extract product details from full content
            prompt = f"""You are extracting product information from a webpage. The user is searching for: "{user_query}"

Page Title: {title}
URL: {url}

Page Content:
{content_excerpt}

IMPORTANT: Look carefully for prices in the content. Prices may appear as:
- Dollar amounts like $999, $1,299, $1,299.99
- "From $X" or "Starting at $X"
- "Was $X, Now $Y" or "Save $X"
- Percentage discounts like "20% off" or "Save 20%"
- Price ranges like "$999-$1,299"

Extract and return ONLY a valid JSON object with these exact fields:
{{
  "product_name": "Specific product name with model (e.g., 'MacBook Air M2 13-inch')",
  "details": "Model, color, storage, configuration (e.g., '256GB, Space Gray, 8GB RAM')",
  "price": "Current price with currency symbol (e.g., '$999' or 'From $999' or '$999-$1,299'). If no price found, use 'Price not available'",
  "deal_info": "Discount, savings, or promotion (e.g., 'Save $200' or '20% off' or 'Black Friday Deal'). Leave empty if none.",
  "in_stock": true
}}

CRITICAL: 
- Search the content thoroughly for any price information
- If you see any dollar amount, percentage, or price-related text, include it in the "price" field
- Do NOT use "Price not available" unless you've searched the entire content and found NO price information
- Return ONLY valid JSON, no markdown, no explanations, no other text"""

            try:
                response = model.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,  # Lower temp for more consistent extraction
                    max_tokens=400
                )
                
                # Parse LLM response
                llm_output = response.choices[0].message.content.strip()
                print(f"🔍 Raw LLM output (first 300 chars): {llm_output[:300]}")
                
                # Remove markdown code blocks if present
                llm_output = re.sub(r'```json\s*', '', llm_output)
                llm_output = re.sub(r'```\s*', '', llm_output)
                llm_output = llm_output.strip()
                print(f"🔍 Cleaned LLM output (first 300 chars): {llm_output[:300]}")
                
                # Try to extract JSON if it's embedded in text
                # Find the first { and try to find matching }
                start_idx = llm_output.find('{')
                if start_idx != -1:
                    # Count braces to find the matching closing brace
                    brace_count = 0
                    end_idx = start_idx
                    for i in range(start_idx, len(llm_output)):
                        if llm_output[i] == '{':
                            brace_count += 1
                        elif llm_output[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    if end_idx > start_idx:
                        llm_output = llm_output[start_idx:end_idx]
                
                product_data = json.loads(llm_output)
                
                # Debug: print the raw product_data
                print(f"🔍 Raw product_data: {product_data}")
                
                # Validate that we have required fields
                # Check if price exists and is not empty/None
                raw_price = product_data.get("price")
                print(f"🔍 Raw price from LLM: {repr(raw_price)} (type: {type(raw_price)})")
                
                if raw_price is None:
                    print(f"⚠️ Price is None, trying to extract from content")
                    # Try to extract price directly from content
                    price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', content_excerpt)
                    if price_match:
                        product_data["price"] = price_match.group(0)
                        print(f"✅ Extracted price from content: {product_data['price']}")
                    elif snippet_price:
                        product_data["price"] = snippet_price
                        print(f"✅ Using price from search snippet: {snippet_price}")
                    else:
                        product_data["price"] = "Price not available"
                        print(f"⚠️ No price found in content or snippet")
                else:
                    # Convert to string and strip whitespace
                    price_value = str(raw_price).strip()
                    if not price_value or price_value.lower() == "price not available" or price_value.lower() == "none" or price_value == "":
                        print(f"⚠️ Price is empty/invalid ('{price_value}'), trying to extract from content")
                        # Try to extract price directly from content as fallback
                        price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', content_excerpt)
                        if price_match:
                            product_data["price"] = price_match.group(0)
                            print(f"✅ Extracted price from content: {product_data['price']}")
                        else:
                            # Last resort: use price from search snippet if available
                            if snippet_price:
                                product_data["price"] = snippet_price
                                print(f"✅ Using price from search snippet: {snippet_price}")
                            else:
                                product_data["price"] = "Price not available"
                                print(f"⚠️ No price found in content or snippet")
                    else:
                        # Keep the price as extracted
                        product_data["price"] = price_value
                        print(f"✅ Price validated: '{price_value}'")
                
                if "product_name" not in product_data or not product_data.get("product_name"):
                    product_data["product_name"] = title
                
                # Add URL and source
                product_data["url"] = url
                product_data["source"] = extract_domain(url)
                
                products.append(product_data)
                print(f"✅ Extracted: {product_data.get('product_name')} - Price: '{product_data.get('price')}' (type: {type(product_data.get('price'))})")
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse LLM JSON response: {e}")
                print(f"LLM output: {llm_output[:200]}")
                # Fallback: try to extract price manually from content
                price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', content_excerpt)
                price = price_match.group(0) if price_match else "Price not available"
                
                products.append({
                    "product_name": title,
                    "details": "",
                    "price": price,
                    "deal_info": "",
                    "url": url,
                    "source": extract_domain(url)
                })
            except Exception as e:
                print(f"Error in LLM extraction: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to basic info
                products.append({
                    "product_name": title,
                    "details": "",
                    "price": "Price not available",
                    "deal_info": "",
                    "url": url,
                    "source": extract_domain(url)
                })
            
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
