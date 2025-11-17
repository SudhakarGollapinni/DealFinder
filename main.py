"""
DealFinder - FastAPI application for finding product deals.
Main entry point with routes and request handling.
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from strands import Agent
from strands_tools import swarm
from strands_tools.tavily import tavily_search, tavily_extract, tavily_crawl
from strands.models.openai import OpenAIModel
from guardrails import SimpleGuardrails, RateLimiter

# Import modules
from templates import render_page
from extractors import extract_and_display_products
from cost_tracker import create_cost_tracker, log_cost_summary

app = FastAPI()

# Initialize guardrails
guardrails = SimpleGuardrails()
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)  # 20 requests per minute


@app.get("/", response_class=HTMLResponse)
def ui_home():
    """Home page with search interface."""
    return render_page("")


@app.post("/swarm", response_class=HTMLResponse)
async def swarm_route(request: Request):
    """Handle search requests and return product deals."""
    form = await request.form()
    user_input = form["msg"]

    # Get client IP for rate limiting
    client_ip = request.client.host

    # 1. Rate limiting check
    rate_allowed, rate_msg = rate_limiter.is_allowed(client_ip)
    if not rate_allowed:
        error_html = f"<div style='color: red;'><strong>⚠️ {rate_msg}</strong></div>"
        return render_page(error_html)

    # 2. Input validation and safety check
    is_safe, safety_msg = guardrails.check_input(user_input)
    if not is_safe:
        error_html = f"<div style='color: red;'><strong>🚫 Input blocked:</strong> {safety_msg}</div>"
        return render_page(error_html)

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
        return render_page(error_html)
    
    # 4. Sanitize input
    sanitized_input = guardrails.sanitize_for_deals(user_input)
    print(f"Processing query: {sanitized_input}")

    # Initialize cost tracker
    cost_tracker = create_cost_tracker()

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
        agent = Agent(
            model=model,
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
            agent,
            cost_tracker
        )
        
        # Log cost summary
        log_cost_summary(cost_tracker)
        
        return render_page(html_output)

    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        error_html = f"<div style='color: red;'>❌ An error occurred. Please try again.</div>"
        return render_page(error_html)
