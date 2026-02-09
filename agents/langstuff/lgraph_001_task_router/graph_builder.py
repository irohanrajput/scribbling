from nodes import classify_task, math_node, text_node, clarify_node, RouterState

from langgraph.graph import StateGraph, END
from langfuse.decorators import observe, langfuse_context

graph = StateGraph(RouterState)

graph.add_node("classifier", classify_task)
graph.add_node("math", math_node)
graph.add_node("text", text_node)
graph.add_node("clarify", clarify_node)


graph.set_entry_point("classifier")

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

graph.add_conditional_edges(
    "classifier",
    route,
    {
        "math": "math",
        "text": "text",
        "unclear": "clarify"
    }
)

graph.add_edge("math", END)
graph.add_edge("text", END)
graph.add_edge("clarify", END)