"""
Product extraction logic for DealFinder.
Handles extraction of product details from search results using Tavily and LLM.
"""
import json
import ast
import re
from typing import List, Dict
from strands import Agent
from strands_tools.tavily import tavily_extract
from utils import extract_text_from_agent_result, extract_domain
from filters import filter_ecommerce_results_with_llm
from html_generator import generate_product_cards_html, convert_agent_json_to_html_simple
from utils import sort_products_by_price


async def extract_and_display_products(result_dict, user_query: str, agent: Agent, cost_tracker: Dict) -> str:
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
        
        # Filter results to only include e-commerce/product sites using LLM
        filtered_results = await filter_ecommerce_results_with_llm(results, agent, cost_tracker)
        
        if not filtered_results:
            return "<div style='color: orange;'>No product pages found. Try a different search or check back later.</div>"
        
        print(f"📊 Filtered {len(results)} results down to {len(filtered_results)} e-commerce sites")
        
        # Parse products using tavily_extract
        products = await parse_products_with_extract(filtered_results, user_query, agent, cost_tracker)
        
        # Sort products by price (lowest first)
        products = sort_products_by_price(products)
        
        # Generate HTML
        return generate_product_cards_html(products)
        
    except Exception as e:
        print(f"Error extracting products: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to simple display
        return convert_agent_json_to_html_simple(result_dict)


async def parse_products_with_extract(results: List[Dict], user_query: str, agent: Agent, cost_tracker: Dict) -> List[Dict]:
    """
    Use tavily_extract to get full page content, then LLM to parse product details
    """
    products = []
    
    # Process up to 9 results (or all if fewer than 9)
    max_results = min(9, len(results))
    for idx, result in enumerate(results[:max_results]):
        try:
            title = result.get("title", "")
            url = result.get("url", "")
            # Check if search result snippet already has a price
            snippet = result.get("content", "") or result.get("raw_content", "") or ""
            snippet_price = None
            snippet_price_backup = None  # Keep backup for fallback
            
            # Quick check: exclude PDFs and obvious non-product pages
            url_lower = url.lower()
            if url_lower.endswith('.pdf') or '/pdf' in url_lower or 'review' in title.lower() or 'comparison' in title.lower():
                print(f"🚫 Skipping {url[:60]}... (PDF or review page)")
                continue
            
            if snippet:
                # Try to extract price from snippet - try multiple patterns
                # Pattern 1: Standard $XXX.XX format
                price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', snippet)
                if price_match:
                    snippet_price = price_match.group(0)
                    snippet_price_backup = snippet_price
                    print(f"💰 Found price in search snippet: {snippet_price}")
                else:
                    # Pattern 2: Price without $ (common in some formats)
                    price_match = re.search(r'(?:price|cost|buy)[:\s]+([\d,]+\.?\d{2})', snippet, re.IGNORECASE)
                    if price_match:
                        snippet_price_backup = f"${price_match.group(1)}"
                        print(f"💰 Found price in snippet (without $): {snippet_price_backup}")
                    else:
                        # Pattern 3: Just numbers that look like prices (XXX.XX format)
                        price_match = re.search(r'\b(\d{1,3}(?:,\d{3})*\.\d{2})\b', snippet)
                        if price_match and float(price_match.group(1).replace(',', '')) < 100000:  # Reasonable price range
                            snippet_price_backup = f"${price_match.group(1)}"
                            print(f"💰 Found potential price in snippet: {snippet_price_backup}")
                
                # Check if snippet looks like a review/article (exclude these)
                snippet_lower = snippet.lower()
                review_indicators = ['review', 'reviewed by', 'our pick', 'best', 'top', 'comparison', 'vs', 'versus', 'pros and cons']
                if any(indicator in snippet_lower[:200] for indicator in review_indicators):
                    print(f"🚫 Skipping {url[:60]}... (looks like review/comparison)")
                    continue
                
                snippet_preview = snippet[:200]
                print(f"📄 Snippet preview: {snippet_preview}")
            
            # If snippet has price AND doesn't look like a review, use it directly
            if snippet_price and not any(indicator in snippet.lower()[:200] for indicator in ['review', 'our pick', 'best', 'comparison']):
                print(f"✅ Using snippet price, skipping full extraction for speed")
                cost_tracker["snippet_based_results"] += 1
                cost_tracker["total_results"] += 1
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
                # For Amazon, use advanced extraction with markdown format (better for structured content)
                # For other sites, use text format
                extract_format = "markdown" if 'amazon.com' in url.lower() else "text"
                extract_depth = "advanced"  # Always use advanced for better content extraction
                
                print(f"🔧 Using extraction format: {extract_format}, depth: {extract_depth} for {url[:60]}")
                
                # tavily_extract expects a list of URLs and is async
                extract_result = await tavily_extract(urls=[url], extract_depth=extract_depth, format=extract_format)
                
                # Track extraction cost
                cost_tracker["tavily_extract_calls"] += 1
                cost_tracker["tavily_extract_cost"] += 0.02  # ~$0.02 per URL (advanced depth)
                cost_tracker["full_extraction_results"] += 1
                
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
                    cost_tracker["total_results"] += 1
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
                cost_tracker["total_results"] += 1
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
                # For Amazon specifically, try to find price in different formats
                if 'amazon.com' in url.lower():
                    # Amazon often has prices in different formats or structured data
                    amazon_price_patterns = [
                        r'\$\d+\.\d{2}',  # $999.99
                        r'\$\d+',  # $999
                        r'price[:\s]+\$[\d,]+',  # price: $999
                        r'[\d,]+\.\d{2}',  # 999.99 (without $)
                    ]
                    for pattern in amazon_price_patterns:
                        matches = re.findall(pattern, content_excerpt, re.IGNORECASE)
                        if matches:
                            print(f"💰 Found Amazon price pattern: {matches[0]}")
                            price_patterns = [f"${matches[0]}" if not matches[0].startswith('$') else matches[0]]
                            break
            
            # Use LLM to extract product details from full content
            # Special handling for Amazon - be more aggressive about finding prices
            amazon_instructions = ""
            if 'amazon.com' in url.lower():
                amazon_instructions = """
SPECIAL INSTRUCTIONS FOR AMAZON:
- Amazon prices may be in various formats: "$999.99", "999.99", "Price: $999", etc.
- Look for price in the first 1000 characters of content (often near the top)
- Check for phrases like "Buy now", "Add to Cart", "List Price", "Price", "Your Price"
- Amazon product pages usually have the price prominently displayed
- If you see any number that looks like a price (with or without $), include it
"""
            
            prompt = f"""You are extracting product information from a webpage. The user is searching for: "{user_query}"

Page Title: {title}
URL: {url}
{amazon_instructions}
Page Content:
{content_excerpt}

IMPORTANT: Look carefully for prices in the content. Prices may appear as:
- Dollar amounts like $999, $1,299, $1,299.99
- "From $X" or "Starting at $X"
- "Was $X, Now $Y" or "Save $X"
- Percentage discounts like "20% off" or "Save 20%"
- Price ranges like "$999-$1,299"
- Numbers that look like prices: 999.99, 1,299.99 (even without $ symbol)

Extract and return ONLY a valid JSON object with these exact fields:
{{
  "product_name": "Specific product name with model (e.g., 'MacBook Air M2 13-inch')",
  "details": "Model, color, storage, configuration (e.g., '256GB, Space Gray, 8GB RAM')",
  "price": "Current price with currency symbol (e.g., '$999' or 'From $999' or '$999-$1,299'). If no price found, use 'Price not available'",
  "deal_info": "Discount, savings, or promotion (e.g., 'Save $200' or '20% off' or 'Black Friday Deal'). Leave empty if none.",
  "in_stock": true
}}

CRITICAL: 
- Search the content thoroughly for any price information, especially in the first 1000 characters
- Look for ANY number that could be a price (with or without $, with or without decimals)
- For e-commerce sites like Amazon, prices are almost always present - search very carefully
- If you see any dollar amount, percentage, or number that looks like a price, include it in the "price" field
- Do NOT use "Price not available" unless you've searched the entire content multiple times and found NO price information
- Return ONLY valid JSON, no markdown, no explanations, no other text"""

            try:
                # Use Strands agent to extract product details
                # Create agent with custom params for extraction
                extract_agent = Agent(
                    model=agent.model,  # Reuse main agent's model
                    system_prompt="You are a product information extractor. Extract product details from web content and return only valid JSON.",
                    params={
                        "temperature": 0.2,  # Lower temp for more consistent extraction
                        "max_tokens": 400
                    }
                )
                
                # Run the agent with the prompt (async)
                agent_result = await extract_agent.invoke_async(prompt)
                
                # Track LLM extraction cost (~$0.002 per product, ~600 tokens)
                cost_tracker["llm_extraction_calls"] += 1
                cost_tracker["llm_extraction_cost"] += 0.002
                
                # Extract text from agent response
                llm_output = extract_text_from_agent_result(agent_result).strip()
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
                    elif snippet_price_backup:
                        product_data["price"] = snippet_price_backup
                        print(f"✅ Using backup price from search snippet: {snippet_price_backup}")
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
                            elif snippet_price_backup:
                                product_data["price"] = snippet_price_backup
                                print(f"✅ Using backup price from search snippet: {snippet_price_backup}")
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
                
                cost_tracker["total_results"] += 1
                products.append(product_data)
                print(f"✅ Extracted: {product_data.get('product_name')} - Price: '{product_data.get('price')}' (type: {type(product_data.get('price'))})")
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse LLM JSON response: {e}")
                print(f"LLM output: {llm_output[:200]}")
                # Fallback: try to extract price manually from content
                price_match = re.search(r'\$[\d,]+(?:\.\d{2})?', content_excerpt)
                price = price_match.group(0) if price_match else "Price not available"
                
                cost_tracker["total_results"] += 1
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
                cost_tracker["total_results"] += 1
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
            cost_tracker["total_results"] += 1
            products.append({
                "product_name": result.get("title", "Product"),
                "details": "",
                "price": "Price not available",
                "deal_info": "",
                "url": result.get("url", "#"),
                "source": extract_domain(result.get("url", ""))
            })
    
    return products

