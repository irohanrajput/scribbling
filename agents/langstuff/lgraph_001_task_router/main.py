from langfuse import Langfuse
from typing import TypedDict
from langchain_groq import ChatGroq

langfuse = Langfuse()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
    )


class RouterState(TypedDict):
    user_input: str
    task_type: str
    result: str


def classify_task(state: RouterState) -> RouterState:
    prompt = f"""
    Classify the user request into one category:
    - math
    - text
    - unclear

    User request:
    {state['user_input']}

    Respond with ONLY one word.
    """
    
    response = llm.invoke(prompt).content.strip().lower()
    
    if response not in {"math", "text", "unclear"}:
        response= "unclear"
        
        
    state["task_type"] = response
    return state
