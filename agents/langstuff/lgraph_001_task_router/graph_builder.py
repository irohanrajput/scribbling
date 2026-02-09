from nodes import classify_task, math_node, text_node, clarify_node, RouterState

from langgraph.graph import StateGraph, END

graph = StateGraph(RouterState)

graph.add_node("classifier", classify_task)
graph.add_node("math", math_node)
graph.add_node("text", text_node)
graph.add_node("clarify", clarify_node)


graph.set_entry_point("classifier")

# conditional routing

def route(state: RouterState):
    return state["task_type"]

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