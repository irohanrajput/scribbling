# Research Assistant Project Flow

Based on my analysis of the project, here's a mermaid flow diagram of the research assistant:

```mermaid
graph TD
    A[User Input: Query] --> B[main.py: Load Environment]
    B --> C[Initialize Gemini LLM]
    C --> D[Create ChatPromptTemplate]
    D --> E[Initialize Tools Array]
    E --> F[tools.py: enhanced_search function]
    F --> G{Query Type Analysis}

    G -->|Stock Query| H[Add finance site filters]
    G -->|Weather Query| I[Add weather forecast modifier]
    G -->|News Query| J[Add latest news modifier]
    G -->|Other| K[Use original query]

    H --> L[DuckDuckGoSearchRun]
    I --> L
    J --> L
    K --> L

    L --> M[Web Search Results]
    M --> N[Create Tool Calling Agent]
    N --> O[AgentExecutor.invoke]
    O --> P[LLM Processing with Search Results]
    P --> Q[Raw Response Generation]
    Q --> R[PydanticOutputParser]
    R --> S[Structured Response]

    S --> T{Parse Success?}
    T -->|Yes| U[Display research_response]
    T -->|No| V[Display Error]

    U --> W[Output: topic, summary, sources, tools_used]
    V --> X[Error Message]

    style A fill:#e1f5fe
    style W fill:#c8e6c9
    style X fill:#ffcdd2
    style F fill:#fff3e0
    style L fill:#f3e5f5
```

## Project Flow Summary:

1. **Entry Point** (`main.py:55`): User provides a research query
2. **Environment Setup** (`main.py:12-17`): Loads environment variables and initializes Gemini LLM
3. **Prompt Configuration** (`main.py:29-45`): Sets up ChatPromptTemplate with system instructions
4. **Tool Processing** (`tools.py:7-21`): Enhanced search function analyzes query type and adds appropriate modifiers
5. **Web Search** (`tools.py:8,21`): DuckDuckGoSearchRun executes the enhanced query
6. **Agent Execution** (`main.py:48-52`): Tool calling agent processes the query with search results
7. **Response Processing** (`main.py:61`): PydanticOutputParser structures the response
8. **Output** (`main.py:62`): Displays structured response with topic, summary, sources, and tools used

The project uses LangChain framework with Gemini LLM to create an intelligent research assistant that enhances user queries and provides structured responses based on real-time web search results.