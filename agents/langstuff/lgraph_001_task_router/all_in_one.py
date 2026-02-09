# ============================================================
# TASK ROUTER - Complete Flow (Single File)
# ============================================================
# This is a LangGraph agent that classifies user input
# and routes it to the right handler (math, text, or clarify).
# ============================================================


# ============================================================
# STEP 1: SETUP - Load environment & imports
# ============================================================
# Load API keys (GROQ_API_KEY, LANGFUSE_*) from .env file
# This MUST happen before anything tries to use those keys.

from dotenv import load_dotenv
load_dotenv()

from typing import TypedDict
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langfuse.decorators import observe, langfuse_context


# ============================================================
# STEP 2: DEFINE THE STATE
# ============================================================
# This is the "shared memory" of the graph.
# Every node receives this dict, reads from it, writes to it,
# and passes it to the next node.
#
# Think of it as a form being passed around an office:
#   - user_input: what the user originally asked
#   - task_type:  filled by classifier ("math", "text", "unclear")
#   - result:     filled by the handler node (final answer)

class RouterState(TypedDict):
    user_input: str
    task_type: str
    result: str


# ============================================================
# STEP 3: CREATE THE LLM
# ============================================================
# One shared LLM instance used by all nodes.
# temperature=0 means no randomness -- same input = same output.

MODEL_NAME = "openai/gpt-oss-120b"

llm = ChatGroq(
    model=MODEL_NAME,
    temperature=0
)


# ============================================================
# STEP 4: LLM WRAPPER (for Langfuse tracing)
# ============================================================
# Every LLM call goes through this function so Langfuse
# can log it as a "generation" -- showing the exact prompt,
# model, response, and token usage in the dashboard.

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


# ============================================================
# STEP 5: DEFINE THE NODES (functions the graph will call)
# ============================================================

# --- NODE 1: CLASSIFIER (always runs first) ---
# This is the "brain" of the router.
# It asks the LLM: "Is this about math, text, or unclear?"
# The LLM responds with ONE word, which gets stored in
# state["task_type"]. The graph reads this to decide
# which node to run next.

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

    # Safety net: if LLM says something unexpected, default to "unclear"
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
    return {"task_type": response}


# --- NODE 2: MATH HANDLER ---
# Only runs if classifier said "math".
# Asks LLM to solve the problem step by step.

@observe(name="math_node")
def math_node(state: RouterState) -> RouterState:
    prompt = f"solve this step by step: \n {state['user_input']}"
    result = call_llm(prompt)
    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=result
    )
    return {"result": result}


# --- NODE 3: TEXT HANDLER ---
# Only runs if classifier said "text".
# Asks LLM to explain clearly and concisely.

@observe(name="text_node")
def text_node(state: RouterState) -> RouterState:
    prompt = f"explain this clearly and concisely: \n{state['user_input']}"
    response = call_llm(prompt)
    langfuse_context.update_current_observation(
        input=state["user_input"],
        output=response
    )
    return {"result": response}


# --- NODE 4: CLARIFY HANDLER ---
# Only runs if classifier said "unclear".
# No LLM call -- just a hardcoded message asking user to rephrase.

@observe(name="clarify_node")
def clarify_node(state: RouterState) -> RouterState:
    langfuse_context.update_current_observation(
        input=state["user_input"],
        output="i need more details to help you. can you clarify ? "
    )
    return {"result": "i need more details to help you. can you clarify ? "}


# ============================================================
# STEP 6: BUILD THE GRAPH (wire nodes together)
# ============================================================
# This is where LangGraph shines. We define:
#   - What nodes exist
#   - Where the graph starts
#   - How nodes connect (fixed edges vs conditional edges)

# Create an empty graph that uses RouterState as shared memory
graph = StateGraph(RouterState)

# Register all 4 nodes (name -> function)
graph.add_node("classifier", classify_task)
graph.add_node("math", math_node)
graph.add_node("text", text_node)
graph.add_node("clarify", clarify_node)

# The graph ALWAYS starts at the classifier
graph.set_entry_point("classifier")


# --- CONDITIONAL ROUTING ---
# After "classifier" runs, this function decides what runs next.
# It reads state["task_type"] (which classify_task just set)
# and returns it. LangGraph then looks up that value in the
# mapping below to find the next node.
#
# Example: classifier sets task_type="text"
#   -> route() returns "text"
#   -> mapping says "text" -> "text" node
#   -> text_node runs next

@observe(name="route_decision")
def route(state: RouterState):
    task_type = state["task_type"]
    # route_map = {"math": "math", "text": "text", "unclear": "clarify"}
    # routed_to = route_map.get(task_type, "clarify")
    # langfuse_context.update_current_observation(
    #     input={"task_type": task_type},
    #     output={"routed_to": routed_to},
    #     metadata={"available_routes": list(route_map.keys())}
    # )
    return task_type


graph.add_conditional_edges(
    "classifier",       # after this node...
    route,              # call this function...
    {                   # and use this mapping:
        "math": "math",         # "math"    -> run math node
        "text": "text",         # "text"    -> run text node
        "unclear": "clarify"    # "unclear" -> run clarify node
    }
)

# After any handler finishes, the graph ends. No loops.
graph.add_edge("math", END)
graph.add_edge("text", END)
graph.add_edge("clarify", END)


# ============================================================
# STEP 7: COMPILE & RUN
# ============================================================
# .compile() turns the graph definition into a runnable app.
# Think: graph_builder draws the blueprint, compile() builds it.

app = graph.compile(interrupt_before=[])


# The main function. Wrapped with @observe so Langfuse
# creates a top-level trace for the entire run.

@observe(name="task-router")
def run_router(user_input: str):
    result = app.invoke({
        "user_input": user_input,   # what the user asked
        "task_type": "",            # empty -- classifier will fill this
        "result": ""                # empty -- handler will fill this
    })
    langfuse_context.update_current_observation(output=result["result"])
    return result


# ============================================================
# STEP 8: EXECUTE
# ============================================================
# This is what actually runs. The full flow:
#
#   "Explain Docker vs VM simply"
#       |
#       v
#   classify_task  -->  LLM says "text"
#       |
#       v
#   route() reads task_type="text"  -->  picks text_node
#       |
#       v
#   text_node  -->  LLM explains Docker vs VM
#       |
#       v
#   END  -->  result printed
#

output = run_router("Explain Docker vs VM simply")
print(output["result"])
