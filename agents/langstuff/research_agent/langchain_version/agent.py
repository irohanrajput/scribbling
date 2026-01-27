"""
=============================================================================
LANGCHAIN VERSION - RESEARCH ASSISTANT (Simple Approach)
=============================================================================

This demonstrates the LANGCHAIN way of building a tool-using agent.
We use a simple approach that works reliably with different models.

KEY CONCEPTS:
1. LLM with tools bound - The model knows about available tools
2. Tool calling - The model generates structured tool calls
3. Manual loop - We handle the tool execution loop ourselves

This approach gives you visibility into what's happening while still
being simpler than the full LangGraph implementation.

AFTER THIS: See the LangGraph version for advanced features like:
- Explicit state management
- Conditional routing
- Checkpointing
- Human-in-the-loop
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Langfuse for observability (v3 API)
from langfuse import Langfuse, observe

# Our tools
from tools.tools import get_all_tools, clear_notes

# Load environment variables
load_dotenv()


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
SYSTEM_PROMPT = """You are a Research Assistant AI that helps users find, analyze, and organize information.

AVAILABLE TOOLS:
1. web_search - Search the internet for current information
2. calculator - Perform mathematical calculations
3. save_note - Store important findings for later
4. get_notes - Retrieve saved notes
5. summarizer - Condense text into key points
6. get_current_time - Get current date/time
7. word_count - Count words/characters in text
8. analyze_text - Analyze text patterns
9. compare_values - Compare two values

IMPORTANT: Use multiple tools to provide comprehensive answers!
- First, search for information
- Then, analyze or calculate as needed
- Save key findings as notes
- Finally, summarize your findings

Always use at least 2-3 tools when possible to demonstrate thorough research."""


def create_langchain_agent():
    """
    Create a simple LangChain agent with tools.

    KEY CONCEPTS:
    -------------
    1. ChatGroq - The LLM (works with Groq's API)
    2. bind_tools() - Tells the model about available tools
    3. The model will output tool_calls when it wants to use a tool

    This is SIMPLER than LangGraph but gives you less control.
    You'll see the difference when you run the LangGraph version.
    """

    # =========================================================================
    # STEP 1: Initialize the LLM
    # =========================================================================
    llm = ChatGroq(
        model=os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile"),
        temperature=0,
    )

    # =========================================================================
    # STEP 2: Get our tools
    # =========================================================================
    tools = get_all_tools()
    print(f"Loaded {len(tools)} tools: {[t.name for t in tools]}")

    # =========================================================================
    # STEP 3: Bind tools to the model
    # =========================================================================
    # This tells the model about the tools and how to call them
    # The model will generate structured tool_calls when it wants to use a tool
    llm_with_tools = llm.bind_tools(tools)

    # Create a tools dictionary for easy lookup
    tools_dict = {tool.name: tool for tool in tools}

    return llm_with_tools, tools_dict


def run_agent_loop(query: str, llm_with_tools, tools_dict, max_iterations: int = 5):
    """
    Run the agent loop manually.

    THE ReAct LOOP:
    ---------------
    1. User sends a message
    2. LLM thinks and may request tool calls
    3. We execute the tools and send results back
    4. LLM sees results and may request more tools or give final answer
    5. Repeat until LLM gives a final answer (no tool calls)

    LIMITATION vs LANGGRAPH:
    ------------------------
    - We handle the loop manually (simple but inflexible)
    - No built-in state management
    - No conditional routing between steps
    - No checkpointing or persistence
    """
    print("\n" + "=" * 60)
    print(f"QUERY: {query}")
    print("=" * 60)

    # Initialize messages with system prompt and user query
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]

    print(f"\n[USER]: {query}")

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1} ---")

        # =====================================================================
        # STEP 1: Call the LLM
        # =====================================================================
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # =====================================================================
        # STEP 2: Check if the LLM wants to use tools
        # =====================================================================
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print(f"[LLM] Requesting {len(response.tool_calls)} tool call(s)")

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                print(f"\n[TOOL CALL] {tool_name}")
                print(f"  Args: {tool_args}")

                # Execute the tool
                if tool_name in tools_dict:
                    tool = tools_dict[tool_name]
                    try:
                        result = tool.invoke(tool_args)
                        print(f"[TOOL RESULT] {result[:150]}..." if len(str(result)) > 150 else f"[TOOL RESULT] {result}")
                    except Exception as e:
                        result = f"Error: {str(e)}"
                        print(f"[TOOL ERROR] {result}")
                else:
                    result = f"Unknown tool: {tool_name}"
                    print(f"[TOOL ERROR] {result}")

                # Add tool result to messages
                messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

        else:
            # =====================================================================
            # STEP 3: LLM gave a final answer (no tool calls)
            # =====================================================================
            print("\n[LLM] Final answer ready")

            print("\n" + "=" * 60)
            print("FINAL ANSWER:")
            print("=" * 60)
            print(response.content)

            return response.content

    print("\n[WARNING] Max iterations reached without final answer")
    return messages[-1].content if messages else "No response generated"


def setup_langfuse():
    """Set up Langfuse for observability."""
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or os.getenv("LANGFUSE_PUBLIC_KEY") == "xxxx":
        print("LANGFUSE not configured. Skipping observability.")
        print("To enable: Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
        return None

    try:
        langfuse = Langfuse()
        print("Langfuse observability enabled!")
        return langfuse
    except Exception as e:
        print(f"Langfuse setup failed: {e}")
        return None


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Clear any previous notes
    clear_notes()

    print("=" * 60)
    print("LANGCHAIN AGENT - SIMPLE TOOL CALLING")
    print("=" * 60)

    # Create the agent
    print("\n[1] Creating agent...")
    llm_with_tools, tools_dict = create_langchain_agent()
    print("Agent created!")

    # Setup Langfuse (optional)
    print("\n[2] Setting up observability...")
    langfuse = setup_langfuse()

    # Run example query
    print("\n[3] Running example query...")

    example_queries = [
        "What is LangGraph and how is it different from LangChain? Save the key differences as a note.",
        # "Calculate 15% of 250, then search for tips on calculating percentages.",
    ]

    for query in example_queries[:1]:
        result = run_agent_loop(query, llm_with_tools, tools_dict)

    # ==========================================================================
    # KEY TAKEAWAYS
    # ==========================================================================
    print("\n" + "=" * 60)
    print("LANGCHAIN APPROACH - KEY TAKEAWAYS:")
    print("=" * 60)
    print("""
    WHAT WE DID:
    1. Created an LLM with tools bound to it
    2. Manually ran a loop: LLM -> Tools -> LLM -> ...
    3. Checked for tool_calls to know when to execute tools
    4. Stopped when LLM gave a response without tool calls

    LIMITATIONS:
    - Manual loop management (we wrote the for loop)
    - No built-in state beyond the messages list
    - No conditional routing (can't branch to different handlers)
    - No checkpointing (can't save and resume)
    - No parallel tool execution

    NEXT: Run the LangGraph version to see how it solves these!

    The LangGraph version shows:
    - Explicit graph structure (nodes and edges)
    - Custom state management
    - Conditional routing with should_continue()
    - Built-in streaming and debugging
    - Checkpointing with MemorySaver
    """)
