from langchain.tools import tool
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Field, Optional, TypedDict, Literal, Annotated
from langchain.messages import AnyMessage, SystemMessage
import operator
from langchain_tavily import TavilySearch
import os
from tavily import AsyncTavilyClient

load_dotenv()

tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


class GeneratedWebSearchQueries(BaseModel):
    queries: List[str] = Field(description="A list of web queries that are generated to find the best candidates for the item")

class ItemDescription(BaseModel):
    category: Literal["clothing", "furniture","electronics"] = Field(description="The category of the item")
    brand: str = Field(default=None, description="The brand of the item in recognized")
    colors: List[str] = Field(default=[], description="A list of colors that are present in the item. This is usually a list of colors that are easy to understand and convert to a color. For example, if the colors are red, blue, and green, you should return ['red', 'blue', 'green']. If the colors are black and white, you should return ['black', 'white']. If the colors are red, blue, and green, you should return ['red', 'blue', 'green'].")
    materials: List[str] = Field(default=[], description="A list of materials that are present in the item. This is usually a list of materials that are easy to understand and convert to a material. For example, if the materials are cotton, wool, and silk, you should return ['cotton', 'wool', 'silk']. If the materials are leather, you should return ['leather']. If the materials are cotton, wool, and silk, you should return ['cotton', 'wool', 'silk']. If the material is wood, you should return ['wood']. And if the material cannot be determined, you should return None.")
    price: float = Field(default=None, description="The price of the item. This is usually a number that is easy to understand and convert to a currency. For example, if the price is $100, you should return 100. If the price is $100.00, you should return 100.00. If the price is $100.00 USD, you should return 100.00 USD.")
    url: str = Field(default=None, description="The URL of the item. This is usually a URL to the item. If the item is not found, you should return None.")
    image_description: str = Field(default=None, description="The description of the image. This is usually a description of the image that is easy to understand and convert to a description. For example, if the image is a shirt, you should return 'shirt'. If the image is a dress, you should return 'dress'. If the image is a coffee mug, you should return 'coffee mug'. If the image is a coffee cup, you should return 'coffee cup'. If the image is a coffee pot, you should return 'coffee pot'. If the image is a coffee maker, you should return 'coffee maker'. If the image is a coffee grinder, you should return 'coffee grinder'. If the image is a coffee bean, you should return 'coffee bean'. If the image is a coffee bean grinder, you should return 'coffee bean grinder'.")

class AffordAgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    original_item_description: Optional[ItemDescription] = Field(default=None, description="The original item description that was provided by the user")
    candidates: List[ItemDescription] = Field(default=[], description="A list of item descriptions that are candidates for the item that was provided by the user")



model = init_chat_model(model="google/gemini-3-flash-preview", temperature=0)



@tool
async def get_item_description(image_path: str) -> ItemDescription:
    """Analyse an image and return a description of the image"""

    model_with_structured_output = model.with_structured_output(ItemDescription)

    response = await model_with_structured_output.ainvoke({
        "messages": [
            SystemMessage(content="You are a helpful assistant that can analyse images and return a description of the image"),
            HumanMessage(content=image_path)
        ]
    })

    return response.item_description
    



@tool
async def expansive_search(item_description: ItemDescription):
    """Given the original item description, perform an expansive search to find the best candidates for the item. It returns a list of URLS for potential items"""
    
    #first we will start by building a query for the web search

    model_with_structured_output = model.with_structured_output(GeneratedWebSearchQueries)

    initial_query = " " += s for s in item_description.values() if s

    response = await model_with_structured_output.ainvoke({
        "messages": [
            SystemMessage(content="You are a helpful assistant that can generate web search queries to find the best candidates for the item"),
            HumanMessage(content=f"Generate 3 web search queries to find the best candidates for the item with the following descriptions: {initial_query}")
        ]
    })

    queries = response.queries

    for query in queries:
        # now for the given query we have the image as well as the descriptions
        response = await tavily_client.search(query=query, include_images=True, search_depth="advanced", max_results=2, include_image_description=True)

        #  now here a good thing to do would be to compare the image descriptions with the item description and see if they are similar, if they are, then we can append to responses. We can use an LLM to do that.
        results.append(response)


    for result in results:
        for image in result.images:
            image_description = image.description
            image_url = image.url
            

    

    






tools = [get_item_description, get_item_price]
model.bind_tools(tools)


async def perform_search(state: AffordAgentState):
    """Perform a search for an item"""

    response = await model.ainvoke({

        "messages": state["messages"],
    })