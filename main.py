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
    <title>Deal Finder</title>
</head>
<body>
    <h1>Find your Favourite Deals</h1>

    <form method="post" action="/swarm">
        <input type="text" name="msg" style="width:300px;" placeholder="Ask something..."/>
        <button type="submit">Send</button>
    </form>

    <hr>
    <div>{{response}}</div>
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
                      system_prompt="You are a deal finding assistant, create a swarm of agents which can use the tavily tools imported above to find best deals for the user based on their query"
                      )
        # Real-time web search
        result = agent.tool.tavily_search(
            query=sanitized_input,
            search_depth="advanced",
            topic="general",
            max_results=10,
            include_raw_content=False
        )
        html_output = convert_agent_json_to_html(result)

        # Check output safety (uncomment if needed)
        output_safe, output_msg = guardrails.check_output(html_output)
        if not output_safe:
            return html_page.replace("{{response}}", 
                f"<div style='color: orange;'>⚠️ Response filtered for safety</div>")
        

        # Check output safety 
        output_safe, output_msg = guardrails.check_output(html_output)
        if not output_safe:
            return html_page.replace("{{response}}",
                                     f"<div style='color: orange;'>⚠️ Response filtered for safety</div>")

        return html_page.replace("{{response}}", html_output)

    except Exception as e:
        print(f"Error processing request: {e}")
        error_html = f"<div style='color: red;'>❌ An error occurred. Please try again.</div>"
        return html_page.replace("{{response}}", error_html)



import json
import ast

def convert_agent_json_to_html(result_dict):
    """
    Converts your agentic JSON to HTML for display.
    - Extracts titles + URLs
    - Formats as clickable links
    """

    # Extract "text" field inside content[0]
    text_block = result_dict["content"][0]["text"]

    # Convert inner string → dict
    inner_data = ast.literal_eval(text_block)

    results = inner_data.get("results", [])

    # Build HTML
    html_parts = ["<h3>Search Results</h3>", "<ul>"]

    for r in results:
        title = html.escape(r.get("title", "No title"))
        url = r.get("url", "#")

        html_parts.append(
            f"<li><a href='{url}' target='_blank'>{title}</a></li>"
        )

    html_parts.append("</ul>")

    return "\n".join(html_parts)
