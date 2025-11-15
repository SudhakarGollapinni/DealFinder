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

app = FastAPI()

html_page = """
<!DOCTYPE html>
<html>
<head>
    <title>Chat UI</title>
</head>
<body>
    <h1>My Chat UI</h1>

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
    input = form["msg"]
    print(input)
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
        query=input,
        search_depth="advanced",
        topic="general",
        max_results=10,
        include_raw_content=False
    )
    html_output = convert_agent_json_to_html(result)
    return html_page.replace("{{response}}", html_output)


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
