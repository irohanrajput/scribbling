from nodes import classify_task, math_node, text_node, clarify_node, RouterState, validate_classification

from langgraph.graph import StateGraph, END
from langfuse.decorators import observe, langfuse_context

graph = StateGraph(RouterState)

# register nodes
graph.add_node("classifier", classify_task)
graph.add_node("validate", validate_classification)
graph.add_node("math", math_node)
graph.add_node("text", text_node)
graph.add_node("clarify", clarify_node)

# fixed edges
graph.set_entry_point("classifier")
graph.add_edge("classifier", "validate")
graph.add_edge("math", END)
graph.add_edge("text", END)
graph.add_edge("clarify", END)


# after validate: retry or route to handler
@observe(name="validation_route")
def validation_route(state: RouterState):
    task_type = state["task_type"]
    retries = state.get("retries", 0)

    if task_type == "unclear" and retries < 2:
        decision = "retry"
    else:
        decision = task_type

    langfuse_context.update_current_observation(
        input={"task_type": task_type, "retries": retries},
        output={"decision": decision},
        metadata={"step": "3_route", "max_retries": 2}
    )
    return decision


graph.add_conditional_edges(
    "validate",
    validation_route,
    {
        "retry": "classifier",
        "math": "math",
        "text": "text",
        "unclear": "clarify"
    }
)

