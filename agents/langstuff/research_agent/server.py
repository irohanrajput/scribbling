"""
FastAPI server for Research Agent - exposes both LangChain and LangGraph agents.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import agents
from langchain_version.agent import create_langchain_agent, run_agent_loop
from langgraph_version.graph import create_research_graph, run_graph
from tools.tools import clear_notes

app = FastAPI(
    title="Research Agent API",
    description="API endpoints for LangChain and LangGraph research agents",
    version="1.0.0",
)

# Initialize agents on startup
langchain_llm = None
langchain_tools = None
langgraph_graph = None


class QueryRequest(BaseModel):
    query: str = Field(..., description="The research query to process", min_length=1)
    max_iterations: int = Field(default=5, description="Maximum iterations for the agent", ge=1, le=10)


class AgentResponse(BaseModel):
    query: str
    response: str
    agent_type: str


@app.on_event("startup")
async def startup_event():
    """Initialize agents on server startup."""
    global langchain_llm, langchain_tools, langgraph_graph

    print("Initializing agents...")

    # Initialize LangChain agent
    langchain_llm, langchain_tools = create_langchain_agent()
    print("LangChain agent ready")

    # Initialize LangGraph agent
    langgraph_graph = create_research_graph()
    print("LangGraph agent ready")

    print("Server ready!")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Research Agent API is running",
        "endpoints": {
            "/langchain": "POST - Run query with LangChain agent",
            "/langgraph": "POST - Run query with LangGraph agent",
            "/docs": "GET - OpenAPI documentation",
        }
    }


@app.post("/langchain", response_model=AgentResponse)
async def langchain_endpoint(request: QueryRequest):
    """
    Run a query using the LangChain agent.

    This agent uses a simple ReAct loop with tool calling.
    """
    global langchain_llm, langchain_tools

    if langchain_llm is None or langchain_tools is None:
        raise HTTPException(status_code=503, detail="LangChain agent not initialized")

    # Clear notes for fresh run
    clear_notes()

    try:
        result = run_agent_loop(
            query=request.query,
            llm_with_tools=langchain_llm,
            tools_dict=langchain_tools,
            max_iterations=request.max_iterations
        )

        return AgentResponse(
            query=request.query,
            response=result or "No response generated",
            agent_type="langchain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/langgraph", response_model=AgentResponse)
async def langgraph_endpoint(request: QueryRequest):
    """
    Run a query using the LangGraph agent.

    This agent uses an explicit graph with state management,
    conditional routing, and checkpointing.
    """
    global langgraph_graph

    if langgraph_graph is None:
        raise HTTPException(status_code=503, detail="LangGraph agent not initialized")

    # Clear notes for fresh run
    clear_notes()

    try:
        final_state = run_graph(
            query=request.query,
            graph=langgraph_graph,
            langfuse_handler=None
        )

        # Extract final answer from state
        response_text = "No response generated"
        if final_state and final_state.get("messages"):
            from langchain_core.messages import AIMessage
            for msg in reversed(final_state["messages"]):
                if isinstance(msg, AIMessage) and msg.content:
                    tool_calls = getattr(msg, 'tool_calls', None)
                    if not tool_calls:
                        response_text = msg.content
                        break

        return AgentResponse(
            query=request.query,
            response=response_text,
            agent_type="langgraph"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
