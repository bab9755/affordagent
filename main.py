from langchain.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict, Literal, Annotated
from langchain.messages import AnyMessage, SystemMessage, HumanMessage
import operator
import os
from tavily import AsyncTavilyClient
from langgraph.graph import StateGraph, START, END
import asyncio


load_dotenv()


class ItemPrice(BaseModel):
    price: float = Field(description="The price of the item")


class ItemDescription(BaseModel):
    category: Literal["clothing", "furniture", "electronics"] = Field(description="The category of the item")
    brand: str = Field(default="", description="The brand of the item if recognized")
    colors: List[str] = Field(default=[], description="A list of colors present in the item")
    materials: List[str] = Field(default=[], description="A list of materials present in the item")
    price: float = Field(default=0.0, description="The price of the item (0 if unknown)")
    url: str = Field(default="", description="The URL of the item")
    image_description: str = Field(default="", description="A description of the item from the image")

class ItemSearchInput(BaseModel):
    category: Literal["clothing", "furniture", "electronics"] = Field(description="The category of the item")
    brand: str = Field(default="", description="The brand of the item")
    colors: str = Field(default="", description="Main colors of the item, comma-separated")
    materials: str = Field(default="", description="Main materials of the item, comma-separated")
    description: str = Field(default="", description="A description of the item")


class Candidates(BaseModel):
    candidates: List[ItemDescription] = Field(default=[], description="A list of item descriptions that are candidates")


class GeneratedWebSearchQueries(BaseModel):
    queries: List[str] = Field(description="A list of web queries to find the item")



class AffordAgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    original_item_description: Optional[ItemDescription]
    candidates: Optional[List[ItemDescription]]


tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

model = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


SYSTEM_PROMPT = open("prompt.md", "r").read()


@tool
async def get_item_description(image_url: str) -> ItemDescription:
    """Analyse an image and return a description of the item"""
    
    model_with_structured_output = model.with_structured_output(ItemDescription)
    
    response = await model_with_structured_output.ainvoke([
        SystemMessage(content="You are a helpful assistant that analyzes images and extracts item details. Identify the category, brand, colors, materials, and provide a description."),
        HumanMessage(content=[
            {"type": "text", "text": "Analyze this image and extract the item details:"},
            {"type": "image_url", "image_url": {"url": image_url}}
        ])
    ])
    
    return response


@tool
async def expansive_search(item_search: ItemSearchInput) -> List[ItemDescription]:
    """Given an item description, perform a web search to find similar items with prices"""
    
    # Build search query from item description
    query_parts = []
    if item_search.brand:
        query_parts.append(item_search.brand)
    if item_search.description:
        query_parts.append(item_search.description)
    if item_search.colors:
        query_parts.append(item_search.colors)
    if item_search.materials:
        query_parts.append(item_search.materials)
    query_parts.append(item_search.category)
    query_parts.append("buy price")
    
    initial_query = " ".join(query_parts)
    
    # Generate additional search queries
    model_with_structured_output = model.with_structured_output(GeneratedWebSearchQueries)
    
    query_response = await model_with_structured_output.ainvoke([
        SystemMessage(content="Generate 2 diverse web search queries to find this item for purchase. Include price-related terms."),
        HumanMessage(content=f"Item: {initial_query}")
    ])
    
    all_queries = [initial_query] + query_response.queries
    
    # Search with all queries
    all_results = []
    all_images = []
    for query in all_queries:
        try:
            response = await tavily_client.search(
                query=query, 
                include_images=True, 
                search_depth="basic", 
                max_results=3
            )
            print(response)
            # 'results' contains dicts with url, title, content
            all_results.extend(response.get("results", []))
            # 'images' contains just URL strings
            all_images.extend(response.get("images", []))
        except Exception as e:
            print(f"Search error for query '{query}': {e}")
    
    # Convert results to candidates
    candidates = []
    for result in all_results[:10]:  # Limit to top 10
        candidate = ItemDescription(
            category=item_search.category,
            url=result.get("url", ""),
            image_description=f"{result.get('title', '')} - {result.get('content', '')}"
        )
        candidates.append(candidate)
    
    # Also add image URLs as candidates (if we want to include them)
    for img_url in all_images[:5]:
        candidate = ItemDescription(
            category=item_search.category,
            url=img_url,
            image_description="Image result"
        )
        candidates.append(candidate)
    
    return candidates


tools = [get_item_description, expansive_search]
model_with_tools = model.bind_tools(tools)


async def agent_node(state: AffordAgentState):
    """Main agent node that processes messages and decides actions"""
    
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = await model_with_tools.ainvoke(messages)
    
    return {"messages": [response]}


async def tool_node(state: AffordAgentState):
    """Execute tools based on the last message"""
    
    last_message = state["messages"][-1]
    results = []
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name == "get_item_description":
            result = await get_item_description.ainvoke(tool_args)
            # Store the original description in state
            return {
                "messages": [{"role": "tool", "content": result.model_dump_json(), "tool_call_id": tool_call["id"]}],
                "original_item_description": result
            }
        elif tool_name == "expansive_search":
            # Convert dict to ItemSearchInput if needed
            if isinstance(tool_args.get("item_search"), dict):
                item_search = ItemSearchInput(**tool_args["item_search"])
            else:
                # Build from original_item_description if available
                orig = state.get("original_item_description")
                if orig:
                    item_search = ItemSearchInput(
                        category=orig.category,
                        brand=orig.brand,
                        colors=", ".join(orig.colors) if orig.colors else "",
                        materials=", ".join(orig.materials) if orig.materials else "",
                        description=orig.image_description
                    )
                else:
                    item_search = None
            
            if item_search:
                result = await expansive_search.ainvoke({"item_search": item_search})
                return {
                    "messages": [{"role": "tool", "content": str([c.model_dump() for c in result]), "tool_call_id": tool_call["id"]}],
                    "candidates": result
                }
    
    return {"messages": []}


def should_continue(state: AffordAgentState) -> str:
    """Determine if we should continue to tools or end"""
    
    last_message = state["messages"][-1]
    
    if last_message.tool_calls:
        return "tools"
    return "end"

graph = StateGraph(AffordAgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "end": END
    }
)
graph.add_edge("tools", "agent")

app = graph.compile()
async def run_agent(image_url: str):
    """Run the agent with an image URL"""
    
    initial_state = {
        "messages": [
            HumanMessage(content=f"Please analyze this item and find similar products with prices: {image_url}")
        ],
        "original_item_description": None,
        "candidates": None
    }
    
    print("🚀 Starting AffordAgent...")
    print(f"📷 Analyzing image: {image_url}\n")
    
    async for event in app.astream(initial_state):
        for node_name, node_output in event.items():
            print(f"--- {node_name.upper()} ---")
            if "messages" in node_output: # node output is a state variable
                for msg in node_output["messages"]:
                    if msg.content
                        print(f"Content: {msg.content}")
                    if msg.tool_calls:
                        print(f"Tool calls: {[tc['name'] for tc in msg.tool_calls]}")
            print()
    
    print("✅ Agent completed!")


if __name__ == "__main__":
    test_image = input("Enter image URL (or press Enter for demo): ").strip()
    
    if not test_image:
        test_image = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800"  # White t-shirt
        print(f"Using demo image: {test_image}")
    
    asyncio.run(run_agent(test_image))
