"""
Cost tracking utilities for DealFinder API usage.
Tracks costs for Tavily search/extract and OpenAI LLM calls.
"""
from typing import Dict


def create_cost_tracker() -> Dict:
    """Initialize a new cost tracker dictionary."""
    return {
        "tavily_search": 0.01,  # ~$0.01 per search
        "tavily_extract_calls": 0,
        "tavily_extract_cost": 0.0,  # ~$0.02 per URL (advanced depth)
        "llm_filtering_calls": 0,
        "llm_filtering_cost": 0.0,  # ~$0.002 per call
        "llm_extraction_calls": 0,
        "llm_extraction_cost": 0.0,  # ~$0.002 per product
        "snippet_based_results": 0,
        "full_extraction_results": 0,
        "total_results": 0
    }


def log_cost_summary(cost_tracker: Dict) -> None:
    """Print a formatted cost summary to the console."""
    total_cost = (
        cost_tracker["tavily_search"] +
        cost_tracker["tavily_extract_cost"] +
        cost_tracker["llm_filtering_cost"] +
        cost_tracker["llm_extraction_cost"]
    )
    
    print("\n" + "="*60)
    print("💰 COST SUMMARY")
    print("="*60)
    print(f"Tavily Search:        ${cost_tracker['tavily_search']:.4f}")
    print(f"Tavily Extract:        ${cost_tracker['tavily_extract_cost']:.4f} ({cost_tracker['tavily_extract_calls']} calls × $0.02)")
    print(f"LLM Filtering:         ${cost_tracker['llm_filtering_cost']:.4f} ({cost_tracker['llm_filtering_calls']} calls)")
    print(f"LLM Extraction:        ${cost_tracker['llm_extraction_cost']:.4f} ({cost_tracker['llm_extraction_calls']} calls)")
    print(f"{'─'*60}")
    print(f"TOTAL COST:            ${total_cost:.4f}")
    print(f"\nResults Breakdown:")
    print(f"  • Snippet-based:     {cost_tracker['snippet_based_results']} (no extraction cost)")
    print(f"  • Full extraction:   {cost_tracker['full_extraction_results']} (${cost_tracker['tavily_extract_cost']:.4f})")
    print(f"  • Total products:    {cost_tracker['total_results']}")
    print("="*60 + "\n")

