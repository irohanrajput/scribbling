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
graph.add_edge("classifier", "validate")
graph.add_edge("math", END)
graph.add_edge("text", END)
graph.add_edge("clarify", END)

def validation_route(state: RouterState):
    if state["task_type"] == "unclear" and state["retries"] < 2:
        return "retry"
    return "continue"


def route_node(state: RouterState):
    return state

graph.add_node("router", route_node)
    

def route_decision(state:RouterState):
    return state["task_type"]

graph.add_conditional_edges(
    "validate",
    validation_route,
    {
        "retry": "classifier",
        "continue": "router", #our existing router
    }
)

graph.add_conditional_edges(
    "router",
    route_decision,
    {
        "math":"math",
        "text": "text",
        "unclear": "clarify"
    }
    
    
)




