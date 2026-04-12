from langgraph.graph import StateGraph, END, START
from nodes import State, generate, critique, improve

# build graph
builder = StateGraph(State)

builder.add_node("generate_node", generate)
builder.add_node("critique_node", critique)
builder.add_node("improve_node", improve)

# flow
builder.add_edge(START, "generate_node")
builder.add_edge("generate_node", "critique_node")

# ---- ROUTER to keep calling 'improve' untill demands are met
def router(state: State):
    if state["score"] >= 8:
        print("FINAL", state)
        return "end"

    if state["iteration"] >= 5:
        print(state)
        return "end"

    return "improve"

# flow after 'critique' but conditional

builder.add_conditional_edges(
    "critique_node",
    router,
    {
        "improve": "improve_node",
        "end": END
    }
)

#loop back (will automatically terminated when conditions are met at the router function only)

builder.add_edge("improve_node", "critique_node")

graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke({
        "question": "what is life",
        "iteration": 0
    })
    











 #after critique funtion call router function,  #based on the output from router, we've two directions to go, that we had to define below, 
    # conditional but we're defining conditions
    
# START
#  → generate
#  → critique
#     → (score < 8) → improve → critique → ...
#     → (score >= 8) → END