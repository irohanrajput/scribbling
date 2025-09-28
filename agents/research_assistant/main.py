import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools import search_tool


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro", api_key=GEMINI_API_KEY, disable_streaming=True
)


class research_response(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]


parser = PydanticOutputParser(pydantic_object=research_response)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a research assistant that can search the web for current information.
            ALWAYS use the search tool when the user asks for current/real-time information.
            Base your answer on the actual search results you receive, not on your pre-trained knowledge.
            If you get search results, use that information in your response.
            Wrap the output in this format and provide no other text\n{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

tools = [search_tool]
agent = create_tool_calling_agent(
    llm=llm, prompt=prompt, tools=tools  # must be an array
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

try:
    query = input("what can i research for you??????")
    raw_response = agent_executor.invoke(
        {
            "query": query,
        }
    )
    structured_response = parser.parse(raw_response.get("output"))
    print(structured_response)
except Exception as e:
    print("error:", e)
