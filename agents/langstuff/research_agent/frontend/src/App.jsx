import { useState } from 'react'

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState({ langchain: false, langgraph: false })
  const [results, setResults] = useState({ langchain: null, langgraph: null })
  const [error, setError] = useState(null)

  const runQuery = async () => {
    if (!query.trim()) return

    setError(null)
    setLoading({ langchain: true, langgraph: true })
    setResults({ langchain: null, langgraph: null })

    const fetchAgent = async (endpoint) => {
      try {
        const res = await fetch(`/${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query.trim(), max_iterations: 5 })
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Request failed')
        }
        return await res.json()
      } catch (e) {
        console.error(`${endpoint} error:`, e)
        return { error: e.message }
      }
    }

    // Run both in parallel
    const [lcResult, lgResult] = await Promise.all([
      fetchAgent('langchain'),
      fetchAgent('langgraph')
    ])

    setResults({ langchain: lcResult, langgraph: lgResult })
    setLoading({ langchain: false, langgraph: false })

    if (lcResult.error && lgResult.error) {
      setError('Both agents failed. Is the backend running on port 8000?')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !loading.langchain && !loading.langgraph) {
      runQuery()
    }
  }

  const formatStepType = (type) => {
    const labels = {
      user_input: 'User Input',
      llm_thinking: 'LLM Thinking',
      tool_call: 'Tool Call',
      tool_result: 'Tool Result',
      final_answer: 'Final Answer'
    }
    return labels[type] || type
  }

  const getStepIcon = (type) => {
    const icons = {
      user_input: 'U',
      llm_thinking: 'T',
      tool_call: 'C',
      tool_result: 'R',
      final_answer: 'A'
    }
    return icons[type] || '?'
  }

  // Remove markdown asterisks and clean up formatting
  const cleanText = (text) => {
    if (!text) return ''
    return text
      .replace(/\*\*\*/g, '')  // Remove ***
      .replace(/\*\*/g, '')    // Remove **
      .replace(/\*/g, '')      // Remove *
      .replace(/#{1,6}\s/g, '') // Remove markdown headers
      .trim()
  }

  const renderFlow = (result, isLoading, agentType) => {
    if (isLoading) {
      return (
        <div className="loading">
          <div className="spinner"></div>
          <p>Running {agentType} agent...</p>
        </div>
      )
    }

    if (!result) {
      return (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
          </svg>
          <p>Enter a query to see the flow</p>
        </div>
      )
    }

    if (result.error) {
      return (
        <div className="empty-state">
          <p style={{ color: '#f87171' }}>Error: {result.error}</p>
        </div>
      )
    }

    return (
      <>
        <div className="flow-steps">
          {result.steps.map((step, idx) => (
            <div key={idx} className={`step ${step.step_type}`}>
              <div className="step-dot">{getStepIcon(step.step_type)}</div>
              <div className="step-content">
                <div className="step-header">
                  <span className="step-type">{formatStepType(step.step_type)}</span>
                  <span className="step-time">{step.timestamp_ms}ms</span>
                </div>
                <div className="step-body">
                  {step.step_type === 'tool_call' ? (
                    <>
                      <div className="tool-info">
                        <div className="tool-name">{step.tool_name}</div>
                        <div className="tool-args">
                          {JSON.stringify(step.tool_args, null, 2)}
                        </div>
                      </div>
                    </>
                  ) : step.step_type === 'tool_result' ? (
                    <>
                      {step.tool_name && <strong>{step.tool_name} returned:</strong>}
                      <pre>{step.content}</pre>
                    </>
                  ) : step.step_type === 'final_answer' ? (
                    <div style={{ maxHeight: '200px', overflow: 'auto' }}>
                      {cleanText(step.content).substring(0, 500)}
                      {step.content.length > 500 && '...'}
                    </div>
                  ) : (
                    step.content
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="final-response">
          <h3>Final Response</h3>
          <p>{cleanText(result.response)}</p>
        </div>
      </>
    )
  }

  const isRunning = loading.langchain || loading.langgraph

  return (
    <div className="app">
      <header className="header">
        <h1>Research Agent Flow Visualizer</h1>
        <p>Compare LangChain vs LangGraph execution flows side by side</p>
      </header>

      {error && <div className="error-message">{error}</div>}

      <div className="input-section">
        <div className="input-row">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter your research query... (e.g., 'What is LangGraph?')"
            disabled={isRunning}
          />
          <button onClick={runQuery} disabled={isRunning || !query.trim()}>
            {isRunning ? 'Running...' : 'Run Query'}
          </button>
        </div>
      </div>

      <div className="comparison">
        <div className="agent-panel langchain">
          <div className="panel-header">
            <h2>LangChain Agent</h2>
            {results.langchain?.total_time_ms && (
              <span className="time-badge">{results.langchain.total_time_ms}ms</span>
            )}
          </div>
          <div className="flow-container">
            {renderFlow(results.langchain, loading.langchain, 'LangChain')}
          </div>
        </div>

        <div className="agent-panel langgraph">
          <div className="panel-header">
            <h2>LangGraph Agent</h2>
            {results.langgraph?.total_time_ms && (
              <span className="time-badge">{results.langgraph.total_time_ms}ms</span>
            )}
          </div>
          <div className="flow-container">
            {renderFlow(results.langgraph, loading.langgraph, 'LangGraph')}
          </div>
        </div>
      </div>

      <div className="legend">
        <div className="legend-item">
          <div className="legend-dot user"></div>
          <span>User Input</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot thinking"></div>
          <span>LLM Thinking</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot tool-call"></div>
          <span>Tool Call</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot tool-result"></div>
          <span>Tool Result</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot final"></div>
          <span>Final Answer</span>
        </div>
      </div>
    </div>
  )
}

export default App
