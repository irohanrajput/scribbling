"""
=============================================================================
SHARED TOOLS FOR LANGCHAIN & LANGGRAPH
=============================================================================

These tools will be used by BOTH the LangChain and LangGraph versions.
Using Pydantic models for better schema generation with various LLM providers.
"""

from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field
from typing import Optional
import json
from datetime import datetime

# =============================================================================
# INPUT SCHEMAS (Pydantic models for better compatibility)
# =============================================================================

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query string to look up on the web")

class CalculatorInput(BaseModel):
    expression: str = Field(description="Mathematical expression to evaluate, e.g. '2 + 2' or 'sqrt(16)'")

class SaveNoteInput(BaseModel):
    title: str = Field(description="Short title for the note")
    content: str = Field(description="The content to save")

class SummarizerInput(BaseModel):
    text: str = Field(description="The text to summarize")
    max_points: int = Field(default=3, description="Number of key points to extract")

class WordCountInput(BaseModel):
    text: str = Field(description="Text to count words in")

class TextAnalysisInput(BaseModel):
    text: str = Field(description="Text to analyze")


# =============================================================================
# TOOL 1: WEB SEARCH
# =============================================================================

@tool(args_schema=WebSearchInput)
def web_search(query: str) -> str:
    """Search the web for current information. Returns titles, snippets and URLs."""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))

        if not results:
            return f"No results found for: {query}"

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
        return f"[MOCK] Search results for '{query}': Install duckduckgo-search for real results."
    except Exception as e:
        return f"Search error: {str(e)}"


# =============================================================================
# TOOL 2: CALCULATOR
# =============================================================================

@tool(args_schema=CalculatorInput)
def calculator(expression: str) -> str:
    """Evaluate a math expression. Supports +, -, *, /, **, sqrt, sin, cos, pi, e."""
    import math

    safe_dict = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sqrt": math.sqrt, "sin": math.sin,
        "cos": math.cos, "tan": math.tan, "log": math.log,
        "log10": math.log10, "exp": math.exp, "pi": math.pi, "e": math.e,
    }

    try:
        result = eval(expression.strip(), {"__builtins__": {}}, safe_dict)
        return f"Result: {expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Calculation error: {str(e)}"


# =============================================================================
# TOOL 3: SAVE NOTE
# =============================================================================

_notes_storage: list[dict] = []

@tool(args_schema=SaveNoteInput)
def save_note(title: str, content: str) -> str:
    """Save a note for later reference. Use to store key findings during research."""
    note = {"id": len(_notes_storage) + 1, "title": title, "content": content}
    _notes_storage.append(note)
    return f"Note saved! ID: {note['id']}, Title: {title}"


@tool
def get_notes() -> str:
    """Retrieve all saved notes from memory."""
    if not _notes_storage:
        return "No notes saved yet."

    formatted = ["=== Saved Notes ==="]
    for note in _notes_storage:
        formatted.append(f"\n[#{note['id']}] {note['title']}: {note['content']}")
    return "\n".join(formatted)


# =============================================================================
# TOOL 4: SUMMARIZER
# =============================================================================

@tool(args_schema=SummarizerInput)
def summarizer(text: str, max_points: int = 3) -> str:
    """Extract key points from text. Returns bullet-point summary."""
    sentences = text.replace('\n', ' ').split('.')
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return "Text too short to summarize."

    key_sentences = sorted(sentences, key=len, reverse=True)[:max_points]
    points = [f"  {i}. {s[:200]}{'...' if len(s) > 200 else ''}"
              for i, s in enumerate(key_sentences, 1)]
    return "Key Points:\n" + "\n".join(points)


# =============================================================================
# TOOL 5: GET CURRENT TIME
# =============================================================================

@tool
def get_current_time() -> str:
    """Get the current date and time. Useful for time-sensitive queries."""
    now = datetime.now()
    return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({now.strftime('%A')})"


# =============================================================================
# TOOL 6: WORD COUNT
# =============================================================================

@tool(args_schema=WordCountInput)
def word_count(text: str) -> str:
    """Count words, characters, and sentences in text."""
    words = len(text.split())
    chars = len(text)
    sentences = text.count('.') + text.count('!') + text.count('?')
    return f"Words: {words}, Characters: {chars}, Sentences: {sentences}"


# =============================================================================
# TOOL 7: TEXT ANALYZER
# =============================================================================

@tool(args_schema=TextAnalysisInput)
def analyze_text(text: str) -> str:
    """Analyze text for basic statistics and patterns."""
    words = text.split()
    word_count = len(words)

    # Find most common words (simple)
    word_freq = {}
    for w in words:
        w_clean = w.lower().strip('.,!?()[]{}":;')
        if len(w_clean) > 3:
            word_freq[w_clean] = word_freq.get(w_clean, 0) + 1

    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)

    return (
        f"Analysis:\n"
        f"  Total words: {word_count}\n"
        f"  Avg word length: {avg_word_len:.1f}\n"
        f"  Top words: {', '.join(f'{w}({c})' for w, c in top_words)}"
    )


# =============================================================================
# TOOL 8: COMPARE VALUES
# =============================================================================

class CompareInput(BaseModel):
    value1: str = Field(description="First value to compare")
    value2: str = Field(description="Second value to compare")
    comparison_type: str = Field(default="text", description="Type: 'text' or 'number'")

@tool(args_schema=CompareInput)
def compare_values(value1: str, value2: str, comparison_type: str = "text") -> str:
    """Compare two values. Useful for comparing search results or data points."""
    if comparison_type == "number":
        try:
            n1, n2 = float(value1), float(value2)
            diff = n1 - n2
            pct = ((n1 - n2) / n2 * 100) if n2 != 0 else 0
            return f"Comparison: {n1} vs {n2}\n  Difference: {diff:+.2f}\n  Percentage: {pct:+.1f}%"
        except:
            return "Error: Could not parse as numbers"
    else:
        len1, len2 = len(value1), len(value2)
        common = set(value1.lower().split()) & set(value2.lower().split())
        return f"Text comparison:\n  Length: {len1} vs {len2}\n  Common words: {len(common)}"


# =============================================================================
# HELPERS
# =============================================================================

def get_all_tools():
    """Returns all tools for use with LangChain/LangGraph agents."""
    return [
        web_search,
        calculator,
        save_note,
        get_notes,
        summarizer,
        get_current_time,
        word_count,
        analyze_text,
        compare_values,
    ]


def clear_notes():
    """Clear the notes storage."""
    global _notes_storage
    _notes_storage = []
