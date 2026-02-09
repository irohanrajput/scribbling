from typing import TypedDict
from langchain_groq import ChatGroq
from langfuse.decorators import observe, langfuse_context


MODEL_NAME = "openai/gpt-oss-120b"

llm = ChatGroq(
    model=MODEL_NAME,
    temperature=0
    )


class RouterState(TypedDict):
    user_input: str
    task_type: str
    result: str


@observe(as_type="generation", name="llm_call")
def call_llm(prompt: str) -> str:
    response = llm.invoke(prompt)
    langfuse_context.update_current_observation(
        model=MODEL_NAME,
        input=prompt,
        output=response.content,
        usage={
            "input": response.response_metadata.get("token_usage", {}).get("prompt_tokens"),
            "output": response.response_metadata.get("token_usage", {}).get("completion_tokens"),
            "total": response.response_metadata.get("token_usage", {}).get("total_tokens"),
        }
    )
    return response.content


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

    response = call_llm(prompt).strip().lower()

    if response not in {"math", "text", "unclear"}:
        response = "unclear"

    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=response,
        metadata={
            "classified_as": response,
            "will_route_to": {"math": "math_node", "text": "text_node", "unclear": "clarify_node"}.get(response)
        }
    )
    state["task_type"] = response
    return state


@observe(name="math_node")
def math_node(state: RouterState) -> RouterState:
    prompt = f"solve this step by step: \n {state['user_input']}"
    result = call_llm(prompt)
    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=result
    )
    state["result"] = result
    return state

@observe(name="text_node")
def text_node(state: RouterState) -> RouterState:
    prompt = f"explain this clearly and concisely: \n{state['user_input']}"
    response = call_llm(prompt)
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

