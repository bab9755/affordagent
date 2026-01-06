from langchain.tools import tool
from langchain.agents import create_agent
from langchain.messages import HumanMessage
import os
from pydantic import BaseModel
from typing import Annotated, List
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient

with open("prompts/item_researcher.md", "r") as file:
    system_prompt = file.read()
model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview")

tavily = TavilyClient()


class Queries(BaseModel):
    queries: List[str]


class Urls(BaseModel):
    urls: List[str]


@tool
def generate_search_queries(item_description: str) -> List[str]:
    """get an item description and returs a list of short web search queries to find the item"""

    query_generator = model.with_structured_output(
        Queries, method="json_schema"
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": f"Generate 3 search queries based on the following item description to find good alternatives {item_description}. The final query should be buy + the generated query so we can acess stores and everything"}
        ]
    )

    response = query_generator.invoke([message])

    print(response.queries)

    return response.queries


@tool 
def get_urls(queries: List[str]) -> List[str]: 
    """use the queries to perform web searches and urls to similar items"""
    results = []
    for query in queries:
        result = tavily.search(query, include_images=True, include_image_description=True)
        results += result["images"]

    print(results)
    return results

item_researcher_agent = create_agent(
    model=model,
    tools=[generate_search_queries, get_urls],
    system_prompt=system_prompt
)

query = "stainless steel Seiko wristwatch against a plain white background. The watch features a round silver-toned case and a matching three-link metal bracelet. The dial is a vibrant teal or turquoise color with a sunburst finish. Silver baton-style hour markers are arranged around the face, with a double marker at the 12 o'clock position. A small date window displaying the number '6' is located at the 3 o'clock position. The hour and minute hands are silver with luminescent inserts, and a thin silver second hand sweeps across the dial. The 'SEIKO' logo is printed in silver below the 12 o'clock marker, and tiny text reading 'MOV'T JAPAN' is visible at the very bottom of the dial."

for step in item_researcher_agent.stream(
    {"messages": [{"role": "user", "content": query}]}):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()


