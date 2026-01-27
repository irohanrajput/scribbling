"""
FastAPI server for Research Agent - exposes both LangChain and LangGraph agents.
"""

import os
import sys
import time
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# Load environment variables
load_dotenv()

# Import agent creators
from langchain_version.agent import create_langchain_agent, SYSTEM_PROMPT as LC_SYSTEM_PROMPT
from langgraph_version.graph import create_research_graph, SYSTEM_PROMPT as LG_SYSTEM_PROMPT, AgentState
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools.tools import clear_notes, get_all_tools

app = FastAPI(
    title="Research Agent API",
    description="API endpoints for LangChain and LangGraph research agents with flow visualization",
    version="1.0.0",
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents on startup
langchain_llm = None
langchain_tools = None
langgraph_graph = None


class QueryRequest(BaseModel):
    query: str = Field(..., description="The research query to process", min_length=1)
    max_iterations: int = Field(default=5, description="Maximum iterations for the agent", ge=1, le=10)


class FlowStep(BaseModel):
    step_number: int
    step_type: str  # "user_input", "llm_thinking", "tool_call", "tool_result", "final_answer"
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    timestamp_ms: int


class FlowResponse(BaseModel):
    query: str
    response: str
    agent_type: str
    steps: list[FlowStep]
    total_time_ms: int


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
            "/langchain": "POST - Run query with LangChain agent (with flow)",
            "/langgraph": "POST - Run query with LangGraph agent (with flow)",
            "/docs": "GET - OpenAPI documentation",
        }
    }


@app.post("/langchain", response_model=FlowResponse)
async def langchain_endpoint(request: QueryRequest):
    """
    Run a query using the LangChain agent with detailed flow tracking.
    """
    global langchain_llm, langchain_tools

    if langchain_llm is None or langchain_tools is None:
        raise HTTPException(status_code=503, detail="LangChain agent not initialized")

    clear_notes()
    steps = []
    start_time = time.time()
    step_num = 1

    # Step 1: User input
    steps.append(FlowStep(
        step_number=step_num,
        step_type="user_input",
        content=request.query,
        timestamp_ms=int((time.time() - start_time) * 1000)
    ))
    step_num += 1

    try:
        messages = [
            SystemMessage(content=LC_SYSTEM_PROMPT),
            HumanMessage(content=request.query),
        ]

        final_response = ""

        for iteration in range(request.max_iterations):
            # LLM thinking
            response = langchain_llm.invoke(messages)
            messages.append(response)

            if hasattr(response, 'tool_calls') and response.tool_calls:
                # LLM decided to call tools
                steps.append(FlowStep(
                    step_number=step_num,
                    step_type="llm_thinking",
                    content=f"Iteration {iteration + 1}: Decided to call {len(response.tool_calls)} tool(s)",
                    timestamp_ms=int((time.time() - start_time) * 1000)
                ))
                step_num += 1

                # Execute each tool
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]

                    steps.append(FlowStep(
                        step_number=step_num,
                        step_type="tool_call",
                        content=f"Calling {tool_name}",
                        tool_name=tool_name,
                        tool_args=tool_args,
                        timestamp_ms=int((time.time() - start_time) * 1000)
                    ))
                    step_num += 1

                    # Execute tool
                    if tool_name in langchain_tools:
                        tool = langchain_tools[tool_name]
                        try:
                            result = tool.invoke(tool_args)
                        except Exception as e:
                            result = f"Error: {str(e)}"
                    else:
                        result = f"Unknown tool: {tool_name}"

                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

                    steps.append(FlowStep(
                        step_number=step_num,
                        step_type="tool_result",
                        content=str(result)[:500] + ("..." if len(str(result)) > 500 else ""),
                        tool_name=tool_name,
                        timestamp_ms=int((time.time() - start_time) * 1000)
                    ))
                    step_num += 1
            else:
                # Final answer
                final_response = response.content
                steps.append(FlowStep(
                    step_number=step_num,
                    step_type="final_answer",
                    content=final_response,
                    timestamp_ms=int((time.time() - start_time) * 1000)
                ))
                break

        if not final_response:
            final_response = messages[-1].content if messages else "No response generated"

        return FlowResponse(
            query=request.query,
            response=final_response,
            agent_type="langchain",
            steps=steps,
            total_time_ms=int((time.time() - start_time) * 1000)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/langgraph", response_model=FlowResponse)
async def langgraph_endpoint(request: QueryRequest):
    """
    Run a query using the LangGraph agent with detailed flow tracking.
    """
    global langgraph_graph

    if langgraph_graph is None:
        raise HTTPException(status_code=503, detail="LangGraph agent not initialized")

    clear_notes()
    steps = []
    start_time = time.time()
    step_num = 1

    # Step 1: User input
    steps.append(FlowStep(
        step_number=step_num,
        step_type="user_input",
        content=request.query,
        timestamp_ms=int((time.time() - start_time) * 1000)
    ))
    step_num += 1

    try:
        initial_state = {
            "messages": [HumanMessage(content=request.query)],
            "notes": [],
            "iteration": 0,
        }

        config = {
            "configurable": {
                "thread_id": f"api-thread-{int(time.time())}",
            }
        }

        final_state = None
        prev_msg_count = 1  # Start with 1 (HumanMessage)

        for event in langgraph_graph.stream(initial_state, config, stream_mode="values"):
            final_state = event
            messages = event.get("messages", [])
            iteration = event.get("iteration", 0)

            # Process new messages
            for msg in messages[prev_msg_count:]:
                if isinstance(msg, AIMessage):
                    tool_calls = getattr(msg, 'tool_calls', None)
                    if tool_calls:
                        steps.append(FlowStep(
                            step_number=step_num,
                            step_type="llm_thinking",
                            content=f"Agent node (iteration {iteration}): Decided to call {len(tool_calls)} tool(s)",
                            timestamp_ms=int((time.time() - start_time) * 1000)
                        ))
                        step_num += 1

                        for tc in tool_calls:
                            steps.append(FlowStep(
                                step_number=step_num,
                                step_type="tool_call",
                                content=f"Calling {tc['name']}",
                                tool_name=tc['name'],
                                tool_args=tc['args'],
                                timestamp_ms=int((time.time() - start_time) * 1000)
                            ))
                            step_num += 1
                    elif msg.content:
                        steps.append(FlowStep(
                            step_number=step_num,
                            step_type="final_answer",
                            content=msg.content,
                            timestamp_ms=int((time.time() - start_time) * 1000)
                        ))
                        step_num += 1

                elif isinstance(msg, ToolMessage):
                    steps.append(FlowStep(
                        step_number=step_num,
                        step_type="tool_result",
                        content=msg.content[:500] + ("..." if len(msg.content) > 500 else ""),
                        timestamp_ms=int((time.time() - start_time) * 1000)
                    ))
                    step_num += 1

            prev_msg_count = len(messages)

        # Extract final response
        response_text = "No response generated"
        if final_state and final_state.get("messages"):
            for msg in reversed(final_state["messages"]):
                if isinstance(msg, AIMessage) and msg.content:
                    tool_calls = getattr(msg, 'tool_calls', None)
                    if not tool_calls:
                        response_text = msg.content
                        break

        return FlowResponse(
            query=request.query,
            response=response_text,
            agent_type="langgraph",
            steps=steps,
            total_time_ms=int((time.time() - start_time) * 1000)
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
