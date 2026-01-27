"""
=============================================================================
SHARED TOOLS FOR LANGCHAIN & LANGGRAPH
=============================================================================

These tools will be used by BOTH the LangChain and LangGraph versions.
This demonstrates that the TOOLS themselves don't change - what changes is
HOW they're orchestrated and controlled.

We'll create 4 tools:
1. web_search   - Search the internet for information
2. calculator   - Perform mathematical calculations
3. save_note    - Save important information to memory
4. summarizer   - Summarize long text into key points
"""

from langchain_core.tools import tool
from typing import Annotated
import json

# =============================================================================
# TOOL 1: WEB SEARCH
# =============================================================================
# This tool searches the web using DuckDuckGo (free, no API key needed)
# In production, you'd use Tavily, Serper, or Google Search API

@tool
def web_search(query: Annotated[str, "The search query to look up on the web"]) -> str:
    """
    Search the web for current information about any topic.
    Use this when you need up-to-date information that might not be in your training data.
    Returns search results with titles, snippets, and URLs.
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))

        if not results:
            return f"No results found for: {query}"

        # Format results nicely
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"Result {i}:\n"
                f"  Title: {r.get('title', 'N/A')}\n"
                f"  Summary: {r.get('body', 'N/A')}\n"
                f"  URL: {r.get('href', 'N/A')}"
            )

        return "\n\n".join(formatted)

    except ImportError:
        # Fallback for when duckduckgo-search is not installed
        return f"[MOCK SEARCH] Results for '{query}': This is simulated search data. Install duckduckgo-search for real results."
    except Exception as e:
        return f"Search error: {str(e)}"


# =============================================================================
# TOOL 2: CALCULATOR
# =============================================================================
# A safe calculator that can evaluate mathematical expressions
# This demonstrates tool usage for computational tasks

@tool
def calculator(expression: Annotated[str, "A mathematical expression to evaluate, e.g., '2 + 2 * 3'"]) -> str:
    """
    Evaluate a mathematical expression and return the result.
    Supports: +, -, *, /, **, (), sqrt, sin, cos, tan, log, pi, e
    Examples: "2 + 2", "sqrt(16)", "sin(pi/2)", "10 ** 2"
    """
    import math

    # Define safe mathematical operations
    safe_dict = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
    }

    try:
        # Clean the expression
        expr = expression.strip()

        # Evaluate safely
        result = eval(expr, {"__builtins__": {}}, safe_dict)

        return f"Result: {expression} = {result}"

    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Calculation error: {str(e)}"


# =============================================================================
# TOOL 3: SAVE NOTE
# =============================================================================
# This tool saves notes to a simple in-memory store
# In LangGraph, we'll see how this integrates with STATE management

# Simple in-memory storage (shared across calls within same session)
_notes_storage: list[dict] = []

@tool
def save_note(
    title: Annotated[str, "A short title for the note (max 50 chars)"],
    content: Annotated[str, "The content to save. Keep it concise, single paragraph, no line breaks."]
) -> str:
    """
    Save an important piece of information for later reference.
    Use this to store key findings or facts during research.
    IMPORTANT: Content should be a single paragraph without line breaks.
    Example: save_note(title="Key Finding", content="LangGraph provides more control than LangChain by using explicit graph structures.")
    """
    note = {
        "id": len(_notes_storage) + 1,
        "title": title,
        "content": content
    }
    _notes_storage.append(note)

    return f"Note saved successfully!\n  ID: {note['id']}\n  Title: {title}\n  Content: {content[:100]}{'...' if len(content) > 100 else ''}"


@tool
def get_notes() -> str:
    """
    Retrieve all saved notes from memory.
    Use this to recall previously saved information during your research.
    """
    if not _notes_storage:
        return "No notes saved yet."

    formatted = ["=== Saved Notes ==="]
    for note in _notes_storage:
        formatted.append(
            f"\n[Note #{note['id']}] {note['title']}\n"
            f"{note['content']}"
        )

    return "\n".join(formatted)


# =============================================================================
# TOOL 4: SUMMARIZER
# =============================================================================
# A simple text summarizer - extracts key points from text
# In production, you might call another LLM for this

@tool
def summarizer(
    text: Annotated[str, "The text content to summarize"],
    max_points: Annotated[int, "Maximum number of key points to extract (default 3)"] = 3
) -> str:
    """
    Summarize long text into key bullet points.
    Useful for condensing search results or long documents into digestible information.
    """
    # Simple extractive summarization
    # In production, you'd use an LLM or proper summarization model

    sentences = text.replace('\n', ' ').split('.')
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return "Could not extract summary - text too short or malformed."

    # Take top sentences (simple heuristic: longer sentences often contain more info)
    key_sentences = sorted(sentences, key=len, reverse=True)[:max_points]

    summary_points = []
    for i, sentence in enumerate(key_sentences, 1):
        # Truncate very long sentences
        if len(sentence) > 200:
            sentence = sentence[:200] + "..."
        summary_points.append(f"  {i}. {sentence}")

    return "Key Points:\n" + "\n".join(summary_points)


# =============================================================================
# HELPER: Get all tools as a list
# =============================================================================
def get_all_tools():
    """Returns all tools as a list for use with LangChain/LangGraph agents."""
    return [web_search, calculator, save_note, get_notes, summarizer]


def clear_notes():
    """Clear the notes storage - useful for testing."""
    global _notes_storage
    _notes_storage = []
