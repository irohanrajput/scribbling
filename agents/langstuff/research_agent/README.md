# Research Agent Flow Visualizer

Compare LangChain vs LangGraph agent execution flows side by side.

## Features

- Side-by-side comparison of LangChain and LangGraph agents
- Real-time flow visualization showing tool calls and responses
- 9 built-in tools: web search, calculator, notes, summarizer, and more
- FastAPI backend with detailed step tracking

## Quick Start

```bash
# Run everything with one command
./dev_start.sh
```

This will:
- Start Langfuse via Docker (observability)
- Create Python virtual environment
- Install dependencies
- Kill any processes on ports 8000/3000
- Start backend (http://localhost:8000)
- Start frontend (http://localhost:3000)

**Services:**
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Langfuse | http://localhost:3703 |

## Configuration

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_LLM_MODEL=openai/gpt-oss-120b
MAX_ITERATIONS=100
```

## Available Tools

| Tool | Description |
|------|-------------|
| `web_search` | Search the web for information |
| `calculator` | Evaluate math expressions |
| `save_note` | Store findings for later |
| `get_notes` | Retrieve saved notes |
| `summarizer` | Extract key points from text |
| `get_current_time` | Get current date/time |
| `word_count` | Count words/characters |
| `analyze_text` | Analyze text patterns |
| `compare_values` | Compare two values |

## Example Queries

Try these to see multiple tools in action:

```
What time is it and calculate 15% of 2500
```

```
Search for Python news and count the words in the result
```

## Project Structure

```
research_agent/
├── server.py              # FastAPI server
├── langchain_version/     # LangChain agent implementation
│   └── agent.py
├── langgraph_version/     # LangGraph agent implementation
│   └── graph.py
├── tools/                 # Shared tools
│   └── tools.py
├── frontend/              # React frontend
│   └── src/App.jsx
├── dev_start.sh          # Development startup script
└── requirements.txt
```

## API Endpoints

- `POST /langchain` - Run query with LangChain agent
- `POST /langgraph` - Run query with LangGraph agent
- `GET /docs` - OpenAPI documentation

## Architecture

```
                    ┌─────────────┐
                    │   Frontend  │
                    │  (React)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │
                    │   Server    │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
   │  LangChain  │  │  LangGraph  │  │   Tools     │
   │    Agent    │  │    Agent    │  │  (shared)   │
   └─────────────┘  └─────────────┘  └─────────────┘
```
