from nodes import classify_task, math_node, text_node, clarify_node, RouterState, validate_classification

from langgraph.graph import StateGraph, END
from langfuse.decorators import observe, langfuse_context

graph = StateGraph(RouterState)

graph.add_node("classifier", classify_task)
graph.add_node("math", math_node)
graph.add_node("text", text_node)
graph.add_node("clarify", clarify_node)
graph.add_node("validate", validate_classification)


graph.set_entry_point("classifier")

# graph execution start from here only

# conditional routing

@observe(name="route_decision")
def route(state: RouterState):
    task_type = state["task_type"]
    route_map = {"math": "math", "text": "text", "unclear": "clarify"}
    routed_to = route_map.get(task_type, "clarify")
    langfuse_context.update_current_observation(
        input={"task_type": task_type},
        output={"routed_to": routed_to},
        metadata={"available_routes": list(route_map.keys())}
    )
    return task_type



def validation_route(state: RouterState):
    if state["task_type"] == "unclear" and state["retries"] < 2:
        return "retry"
    return "continue"

graph.add_conditional_edges(
    "validate",
    validation_route,
    {
        "retry":"classifier",
        "continue": "route" #our conventional route
    }
)

graph.add_edge("math", END)
graph.add_edge("text", END)
graph.add_edge("clarify", END)
graph.add_edge("classifier", "validate")

