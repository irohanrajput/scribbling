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
    confidence: float
    retries: int


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
    
    also give the confidence score between 0 and 1.
    
    Format: 
    <category>|<confidence>

    User request:
    {state['user_input']}

    """

    response = call_llm(prompt).strip().lower()
    
    try:
        category, confidence = response.split("|") #unpacking from list
        confidence = float(confidence)
    except Exception:
        category, confidence = "unclear", 0.0
        
    # except Exception as e:
    #     raise e

    if category not in {"math", "text", "unclear"}:
        category, confidence = "unclear", 0.0
        
    state["task_type"] = category
    state["confidence"] = confidence

    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=response,
        metadata={
            "classified_as": response,
            "will_route_to": {"math": "math_node", "text": "text_node", "unclear": "clarify_node"}.get(response)
        }
    )
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

@observe(name="validate_classification")
def validate_classification(state: RouterState) -> RouterState:
    if state["confidence"] < 0.6:
        state["task_type"] = "unclear"
    return state