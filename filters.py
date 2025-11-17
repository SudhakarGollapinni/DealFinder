"""
Result filtering logic for DealFinder.
Uses LLM to filter search results and keep only e-commerce product pages.
"""
import json
import re
from typing import List, Dict
from strands import Agent
from utils import extract_text_from_agent_result, extract_domain


async def filter_ecommerce_results_with_llm(results: List[Dict], agent: Agent, cost_tracker: Dict) -> List[Dict]:
    """
    Use Strands Agent to filter search results and only keep e-commerce/product pages.
    Excludes forums, social media, review sites, articles, etc.
    """
    if not results:
        return []
    
    # Process in batches to be efficient
    batch_size = 5
    filtered_results = []
    
    for i in range(0, len(results), batch_size):
        batch = results[i:i + batch_size]
        
        # Build prompt with batch of results
        results_text = ""
        for idx, result in enumerate(batch):
            title = result.get("title", "")
            url = result.get("url", "")
            snippet = (result.get("content", "") or result.get("raw_content", "") or "")[:300]  # First 300 chars
            
            results_text += f"""
Result {idx + 1}:
- Title: {title}
- URL: {url}
- Snippet: {snippet}
"""
        
        prompt = f"""You are filtering search results to find ONLY actual product purchase pages from e-commerce websites.

CRITICAL: Only include pages where users can actually BUY the product with a price and purchase option.

INCLUDE (actual product purchase pages):
- Product pages on e-commerce sites (Amazon, Best Buy, Target, Walmart, Newegg, etc.) with prices and "Add to Cart" or "Buy Now"
- Product pages on brand stores (Apple.com, Samsung.com, Dell.com, etc.) with prices and purchase options
- Online retailers with product listings that show prices and allow immediate purchase
- Pages that clearly have: product price + purchase button + product specifications

STRICTLY EXCLUDE (NOT product purchase pages):
- Review websites (Wirecutter, CNET reviews, TechRadar reviews, etc.) - even if they mention prices
- Comparison websites or "best of" lists
- PDF files or document downloads
- Product specification sheets or technical documentation
- News articles about products
- Blog posts or articles
- Forums (Reddit, discussion boards)
- Social media (Twitter, Facebook, Instagram)
- YouTube videos
- Q&A sites (Quora, Stack Overflow)
- Wikipedia or informational pages
- Product announcement pages without purchase options
- Press releases or marketing pages without buy buttons

Here are the search results to filter:
{results_text}

IMPORTANT: 
- If a page is a review, comparison, or article (even if it mentions prices), EXCLUDE it
- If a page is a PDF or document, EXCLUDE it
- Only include pages where you can actually purchase the product right now

Return ONLY a JSON array with the indices (1-based) of results that are actual product purchase pages.
Example: [1, 3] means keep results 1 and 3.

Return ONLY the JSON array, no other text."""

        try:
            # Use Strands agent to process the prompt
            # Create a simple agent for filtering (no tools needed)
            filter_agent = Agent(
                model=agent.model,  # Use the same model as the main agent
                system_prompt="You are a search result classifier. Return only JSON arrays."
            )
            
            # Run the agent with the prompt (async)
            agent_result = await filter_agent.invoke_async(prompt)
            
            # Track LLM filtering cost (~$0.002 per batch, ~300 tokens)
            cost_tracker["llm_filtering_calls"] += 1
            cost_tracker["llm_filtering_cost"] += 0.002
            
            # Extract text from agent response
            llm_output = extract_text_from_agent_result(agent_result).strip()
            
            # Remove markdown code blocks if present
            llm_output = re.sub(r'```json\s*', '', llm_output)
            llm_output = re.sub(r'```\s*', '', llm_output)
            llm_output = llm_output.strip()
            
            # Extract JSON array
            start_idx = llm_output.find('[')
            end_idx = llm_output.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                llm_output = llm_output[start_idx:end_idx]
            
            # Parse indices
            indices = json.loads(llm_output)
            
            # Add filtered results
            for idx in indices:
                if 1 <= idx <= len(batch):
                    result = batch[idx - 1]  # Convert to 0-based
                    filtered_results.append(result)
                    domain = extract_domain(result.get("url", ""))
                    print(f"✅ LLM included: {domain} (result {idx} in batch)")
            
            # Log excluded results
            included_indices = set(indices)
            for idx, result in enumerate(batch, 1):
                if idx not in included_indices:
                    domain = extract_domain(result.get("url", ""))
                    print(f"🚫 LLM excluded: {domain} (result {idx} in batch)")
                    
        except Exception as e:
            print(f"⚠️ Error filtering batch with LLM: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: include all if LLM fails
            filtered_results.extend(batch)
    
    return filtered_results

