"""
=============================================================================
LANGGRAPH VERSION - RESEARCH ASSISTANT WITH EXPLICIT GRAPH CONTROL
=============================================================================

This is the LANGGRAPH way of building an agent. Here's what makes it different:

=============================================================================
KEY DIFFERENCES FROM LANGCHAIN:
=============================================================================

1. EXPLICIT GRAPH STRUCTURE
   - You define NODES (functions that do work)
   - You define EDGES (how data flows between nodes)
   - The execution path is VISIBLE and CONTROLLABLE

2. STATE MANAGEMENT
   - State is a typed object that flows through the graph
   - Every node receives state and can modify it
   - You control exactly what data is passed around

3. CONDITIONAL ROUTING
   - You can route to different nodes based on conditions
   - "If tool call -> go to tool_executor, else -> go to end"
   - Much more flexible than LangChain's fixed loop

4. CHECKPOINTING & PERSISTENCE
   - Built-in support for saving/loading state
   - Can resume from any point in execution
   - Perfect for long-running workflows

5. HUMAN-IN-THE-LOOP
   - Can pause execution for human approval
   - Can wait for external input
   - Built-in interrupt mechanism

6. STREAMING & DEBUGGING
   - Stream events as they happen
   - See exactly which node is executing
   - Full visibility into the graph

Let's see how this looks in practice!
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Annotated, TypedDict, Sequence
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# LangGraph imports - THIS IS THE STAR!
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Langfuse for observability (v3 API)
from langfuse import Langfuse, observe

# Our tools
from tools.tools import get_all_tools, clear_notes

# Load environment variables
load_dotenv()


# =============================================================================
# STEP 1: DEFINE THE STATE
# =============================================================================
# In LangGraph, STATE is a typed dictionary that flows through your graph.
# Every node receives the current state and returns updates to it.
#
# This is FUNDAMENTALLY DIFFERENT from LangChain:
# - LangChain: State is hidden inside the AgentExecutor
# - LangGraph: State is explicit, typed, and you control it
#
# The `add_messages` function is a REDUCER - it specifies HOW to update
# the messages list (append, not replace).


def add_messages(left: list, right: list) -> list:
    """Reducer that appends new messages to existing ones."""
    return left + right


class AgentState(TypedDict):
    """
    The state that flows through our graph.

    Think of this as the "memory" of your agent at any point in time.
    Every node can read from and write to this state.

    Fields:
    - messages: The conversation history (human, AI, tool messages)
    - notes: Any notes saved during research (custom field!)
    - iteration: Track how many tool calls we've made
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    notes: list[str]      # Custom state field - try this in LangChain!
    iteration: int        # Track iterations - another custom field


# =============================================================================
# STEP 2: DEFINE THE SYSTEM PROMPT
# =============================================================================
# Notice we DON'T need to describe the ReAct format here!
# LangGraph handles tool calling natively using the model's built-in capability.

SYSTEM_PROMPT = """You are a Research Assistant AI that helps users find, analyze, and organize information.

Your capabilities:
1. WEB SEARCH - Search the internet for current information
2. CALCULATOR - Perform mathematical calculations
3. SAVE/GET NOTES - Store and retrieve important findings
4. SUMMARIZER - Condense long text into key points

Your approach:
- Always be thorough and verify information when possible
- Save important findings using the note-taking tool
- Provide sources and explain your reasoning
- If a calculation is needed, use the calculator - don't guess

Be concise but thorough. Always cite your sources when using search results.
When you have gathered enough information, provide a comprehensive final answer."""


# =============================================================================
# STEP 3: CREATE THE LLM WITH TOOLS BOUND
# =============================================================================

def get_model_with_tools():
    """
    Create an LLM with tools bound to it.

    KEY CONCEPT: Tool Binding
    -------------------------
    Unlike LangChain where tools are passed to an AgentExecutor,
    in LangGraph we BIND tools directly to the model.

    This means the model knows about the tools and can generate
    proper tool calls in its response.
    """
    llm = ChatGroq(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        temperature=0,
    )

    tools = get_all_tools()

    # Bind tools to the model - this is crucial!
    # The model will now generate ToolCall objects when it wants to use a tool
    llm_with_tools = llm.bind_tools(tools)

    return llm_with_tools, tools


# =============================================================================
# STEP 4: DEFINE THE NODES
# =============================================================================
# Nodes are functions that:
# 1. Receive the current state
# 2. Do some work (call LLM, execute tools, etc.)
# 3. Return state updates
#
# This is where LangGraph shines - you have FULL CONTROL over each step!


def agent_node(state: AgentState) -> dict:
    """
    The AGENT node - this is where the LLM thinks and decides.

    This node:
    1. Takes the current conversation state
    2. Calls the LLM with the messages
    3. Returns the LLM's response (which may include tool calls)

    KEY INSIGHT:
    ------------
    In LangChain, thinking + tool execution happens in one opaque loop.
    In LangGraph, thinking (this node) and tool execution (next node)
    are SEPARATE, giving you control points between them!
    """
    print(f"\n[AGENT NODE] Iteration: {state.get('iteration', 0) + 1}")

    llm_with_tools, _ = get_model_with_tools()

    # Create the prompt with system message + conversation history
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # Run the chain
    chain = prompt | llm_with_tools
    response = chain.invoke({"messages": state["messages"]})

    print(f"[AGENT NODE] Response type: {type(response).__name__}")
    tool_calls = getattr(response, 'tool_calls', None)
    if tool_calls:
        print(f"[AGENT NODE] Tool calls: {[tc['name'] for tc in response.tool_calls]}")
    else:
        print("[AGENT NODE] No tool calls - providing final answer")

    # Return state updates
    # The reducer will APPEND the response to existing messages
    return {
        "messages": [response],
        "iteration": state.get("iteration", 0) + 1,
    }


def should_continue(state: AgentState) -> str:
    """
    CONDITIONAL EDGE - Decide where to go next.

    This is a HUGE advantage of LangGraph!
    You can route execution based on ANY condition:
    - Did the LLM want to use a tool?
    - Have we exceeded max iterations?
    - Is human approval required?
    - Any custom business logic!

    Returns:
    - "tools" -> Go to tool_node to execute the tool calls
    - "end" -> We're done, end the graph
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Check if the LLM wants to call tools
    # We use getattr to safely check for tool_calls (not all message types have it)
    tool_calls = getattr(last_message, 'tool_calls', None)
    if tool_calls:
        print(f"[ROUTER] Tool calls detected -> routing to 'tools'")

        # EXAMPLE: Add custom logic here!
        # You could check if a "dangerous" tool is being called
        # and route to a "human_approval" node instead
        #
        # dangerous_tools = ["delete_file", "send_email"]
        # for tc in last_message.tool_calls:
        #     if tc["name"] in dangerous_tools:
        #         return "human_approval"

        return "tools"

    # Check max iterations (prevent infinite loops)
    if state.get("iteration", 0) >= 10:
        print("[ROUTER] Max iterations reached -> ending")
        return "end"

    print("[ROUTER] No tool calls -> ending")
    return "end"


# =============================================================================
# STEP 5: BUILD THE GRAPH
# =============================================================================
# This is where we connect everything together.
# The graph defines:
# - What nodes exist
# - How they connect (edges)
# - Conditional routing logic


def create_research_graph():
    """
    Build the LangGraph workflow.

    GRAPH STRUCTURE:
    ----------------

    START
      |
      v
    [agent] <----+
      |          |
      v          |
    {should_continue}
      |          |
      | tools    |
      v          |
    [tool_node]--+
      |
      | end
      v
     END

    This is the ReAct pattern, but EXPLICITLY defined!
    You can see exactly what's happening and add steps anywhere.
    """
    tools = get_all_tools()

    # =========================================================================
    # Create the graph with our state schema
    # =========================================================================
    workflow = StateGraph(AgentState)

    # =========================================================================
    # Add nodes
    # =========================================================================
    # Each node is a function that transforms state

    # The agent node - calls the LLM
    workflow.add_node("agent", agent_node)

    # The tool node - executes tool calls
    # ToolNode is a prebuilt node that automatically:
    # 1. Extracts tool calls from the last AI message
    # 2. Executes each tool
    # 3. Returns ToolMessages with results
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)

    # =========================================================================
    # Add edges
    # =========================================================================

    # START -> agent: Always start with the agent
    workflow.add_edge(START, "agent")

    # agent -> (conditional): After agent, check what to do
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",  # If tools needed, go to tool node
            "end": END,        # If done, end the graph
        }
    )

    # tools -> agent: After tools execute, go back to agent
    # The agent will see the tool results and decide next steps
    workflow.add_edge("tools", "agent")

    # =========================================================================
    # Compile the graph
    # =========================================================================
    # Compiling creates an executable workflow
    # We add MemorySaver for checkpointing (optional but powerful)

    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)

    return graph


# =============================================================================
# STEP 6: LANGFUSE SETUP
# =============================================================================

def setup_langfuse():
    """
    Set up Langfuse for observability.

    LANGFUSE 3.x INTEGRATION:
    -------------------------
    Langfuse v3 uses a simpler approach with the @observe decorator
    and automatic tracing when environment variables are set.
    """
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or os.getenv("LANGFUSE_PUBLIC_KEY") == "xxxx":
        print("LANGFUSE not configured. Skipping observability.")
        print("To enable: Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
        return None

    try:
        langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        print("Langfuse observability enabled!")
        print("View traces at: https://cloud.langfuse.com")
        return langfuse
    except Exception as e:
        print(f"Langfuse setup failed: {e}")
        return None


# =============================================================================
# STEP 7: RUN THE GRAPH
# =============================================================================

def run_graph(query: str, graph, langfuse_handler=None):
    """
    Execute the graph with a query.

    KEY DIFFERENCE FROM LANGCHAIN:
    ------------------------------
    When you invoke the graph, you can:
    1. Stream events as they happen
    2. See which node is executing
    3. Inspect state at any point
    4. Resume from checkpoints

    The 'thread_id' config enables checkpointing - you can:
    - Pause and resume execution
    - Replay from any state
    - Debug by inspecting intermediate states
    """
    print("\n" + "=" * 60)
    print(f"QUERY: {query}")
    print("=" * 60)

    # Initial state
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "notes": [],
        "iteration": 0,
    }

    # Config for this run
    config = {
        "configurable": {
            "thread_id": "research-thread-1",  # For checkpointing
        }
    }

    try:
        # =====================================================================
        # OPTION 1: Simple invoke (get final result)
        # =====================================================================
        # result = graph.invoke(initial_state, config)

        # =====================================================================
        # OPTION 2: Stream events (see everything that happens!)
        # =====================================================================
        # This is MUCH better for debugging and understanding the flow

        print("\n[STREAMING EXECUTION]")
        print("-" * 40)

        final_state = None
        for event in graph.stream(initial_state, config, stream_mode="values"):
            # Each event is the full state after a node executes
            final_state = event

            # Print the latest message
            if event.get("messages"):
                last_msg = event["messages"][-1]
                msg_type = type(last_msg).__name__

                if msg_type == "HumanMessage":
                    print(f"\n[USER]: {last_msg.content[:100]}...")
                elif msg_type == "AIMessage":
                    tool_calls = getattr(last_msg, 'tool_calls', None)
                    if tool_calls:
                        for tc in tool_calls:
                            print(f"\n[AI TOOL CALL]: {tc['name']}({tc['args']})")
                    elif last_msg.content:
                        print(f"\n[AI RESPONSE]: {last_msg.content[:200]}...")
                elif msg_type == "ToolMessage":
                    print(f"\n[TOOL RESULT]: {last_msg.content[:150]}...")

        # =====================================================================
        # Extract final answer
        # =====================================================================
        print("\n" + "=" * 60)
        print("FINAL ANSWER:")
        print("=" * 60)

        if final_state and final_state.get("messages"):
            # Find the last AI message that's not a tool call
            for msg in reversed(final_state["messages"]):
                if isinstance(msg, AIMessage) and msg.content:
                    msg_tool_calls = getattr(msg, 'tool_calls', None)
                    if not msg_tool_calls:
                        print(msg.content)
                        break

        return final_state

    except Exception as e:
        print(f"Graph execution error: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# BONUS: VISUALIZE THE GRAPH
# =============================================================================

def visualize_graph(graph):
    """
    Print a text representation of the graph structure.

    In production, you can use:
    - graph.get_graph().draw_mermaid() -> Mermaid diagram
    - graph.get_graph().draw_png() -> PNG image (requires graphviz)
    """
    print("\n" + "=" * 60)
    print("GRAPH STRUCTURE")
    print("=" * 60)
    print("""
    +-------+
    | START |
    +---+---+
        |
        v
    +-------+     (if tool calls)    +---------+
    | agent | -------------------->  |  tools  |
    +---+---+                        +----+----+
        |                                 |
        | (no tool calls)                 |
        v                                 |
    +-------+                             |
    |  END  | <---------------------------+
    +-------+

    The agent keeps looping through tools until it has
    enough information to provide a final answer.
    """)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Clear any previous notes
    clear_notes()

    print("=" * 60)
    print("LANGGRAPH RESEARCH ASSISTANT")
    print("=" * 60)

    # Create the graph
    print("\n[1] Building the graph...")
    graph = create_research_graph()

    # Visualize the structure
    visualize_graph(graph)

    # Setup Langfuse
    print("\n[2] Setting up observability...")
    langfuse_handler = setup_langfuse()

    # Run example queries
    print("\n[3] Running example query...")

    example_queries = [
        "What is LangGraph and how is it different from LangChain? Save the key differences as a note.",
        # "Calculate 15% of 250, then search for tips on calculating percentages mentally.",
        # "Find information about Python 3.12 new features and summarize them.",
    ]

    for query in example_queries[:1]:
        run_graph(query, graph, langfuse_handler)

    # ==========================================================================
    # WHAT YOU LEARNED:
    # ==========================================================================
    print("\n" + "=" * 60)
    print("KEY LANGGRAPH CONCEPTS DEMONSTRATED:")
    print("=" * 60)
    print("""
    1. EXPLICIT STATE (AgentState)
       - You define what data flows through your graph
       - Add custom fields like 'notes', 'iteration', etc.
       - State is typed and predictable

    2. NODES AS FUNCTIONS
       - Each node is a simple function
       - Receives state, returns state updates
       - Easy to test and debug

    3. CONDITIONAL EDGES
       - should_continue() decides where to go next
       - Can add ANY custom logic here
       - Route to approval nodes, error handlers, etc.

    4. STREAMING
       - See events as they happen
       - Debug the flow in real-time
       - Better user experience

    5. CHECKPOINTING
       - MemorySaver stores state
       - Resume from any point
       - Great for long-running workflows

    WHAT YOU CAN'T DO IN LANGCHAIN:
    - Add custom state fields (notes, iteration)
    - See the exact graph structure
    - Add conditional routing based on business logic
    - Stream individual node executions
    - Checkpoint and resume
    - Add human-in-the-loop approval easily
    """)
