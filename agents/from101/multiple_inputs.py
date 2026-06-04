from typing import TypedDict, List
from langgraph.graph import StateGraph


class agent_state(TypedDict):
    values: list[int]
    name: str
    result: str
    
    
def process_values(stt)