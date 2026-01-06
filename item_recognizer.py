from langchain.tools import tool
from langchain.agents import create_agent
from langchain.messages import HumanMessage
import os
from pydantic import BaseModel
from typing import Annotated
from langchain_google_genai import ChatGoogleGenerativeAI


with open("prompts/item_recognizer.md", "r") as file:
    system_prompt = file.read()


model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview")

class ItemDescription(BaseModel):
    description: str

model_with_structure = model.with_structured_output(
    ItemDescription, method="json_schema"
)


@tool
def get_item_description(url: Annotated[str, "a url representing the image of the item we want to analyse"]) -> Annotated[str, "A textual description of the item"]:

    """from an image url get the description of the object in the image"""
    message = HumanMessage(
    content=[
        {"type": "text", "text": "Describe the image at the URL."},
        {
            "type": "image",
            "url": url,
        },
        ]
    )
    response = model_with_structure.invoke(
       [message]
    )

    return response.description



item_recognizer_agent = create_agent(
    model=model,
    tools=[get_item_description],
    system_prompt=system_prompt

)

query = "Give me the description of the following item: https://cdn11.bigcommerce.com/s-uzonwrhn18/images/stencil/1280x1280/products/18864/101548/SUR525-01__01328.1710768705.jpg?c=1"

for step in item_recognizer_agent.stream(
    {"messages": [{"role": "user", "content": query}]}
):
    for update in step.values():
        for message in update.get("messages", []):
            message.pretty_print()



