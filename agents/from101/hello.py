from typing import TypedDict, Dict
from langgraph.graph import StateGraph, START, END

class agent_state(TypedDict):
    message: str

state = agent_state(message="rohan")

def greeting_node(state: agent_state) -> agent_state:
    """Simple node that adds a greeting message to the state"""
    state['message'] = f"hey {state['message']} what's up buddyyyyy"
    return state

graph = StateGraph(agent_state)

graph.add_node("greeter",greeting_node)

graph.set_entry_point("greeter")
graph.set_finish_point("greeter")

app = graph.compile()


result = app.invoke({"message":"rohan"})

print(result)