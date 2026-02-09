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


def math_node(state: RouterState) -> RouterState:
    prompt = f"solve this step by step: \n{state["user_input"]}"
    state["result"] = llm.invoke(prompt).content
    return state

def text_node(state: RouterState) -> RouterState:
    prompt = f"explain this clearly and concisely: \n{state["user_input"]}"
    response = llm.invoke(prompt).content
    state["result"] = response
    return state


def clarify_node(state: RouterState) -> RouterState:
    state["result"] = "i need more details to help you. can you clarify ? "
    return state

