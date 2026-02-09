from typing import TypedDict
from langchain_groq import ChatGroq
from langfuse.decorators import observe, langfuse_context


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
    )


class RouterState(TypedDict):
    user_input: str
    task_type: str
    result: str


@observe(name="classify_task")
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

    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=response
    )
    state["task_type"] = response
    return state


@observe(name="math_node")
def math_node(state: RouterState) -> RouterState:
    prompt = f"solve this step by step: \n {state['user_input']}"
    result = llm.invoke(prompt).content
    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=result
    )
    state["result"] = result
    return state

@observe(name="text_node")
def text_node(state: RouterState) -> RouterState:
    prompt = f"explain this clearly and concisely: \n{state['user_input']}"
    response = llm.invoke(prompt).content
    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=response
    )
    state["result"] = response
    return state


@observe(name="clarify_node")
def clarify_node(state: RouterState) -> RouterState:
    langfuse_context.update_current_observation(
        input=state["user_input"],
        output="i need more details to help you. can you clarify ? "
    )
    state["result"] = "i need more details to help you. can you clarify ? "
    return state

