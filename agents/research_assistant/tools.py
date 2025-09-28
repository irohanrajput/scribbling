from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from datetime import datetime


def enhanced_search(query):
    search = DuckDuckGoSearchRun()
    # Add specific search modifiers for better results
    if "stock price" in query.lower() or "stock" in query.lower():
        enhanced_query = (
            f"{query} site:finance.yahoo.com OR site:marketwatch.com OR site:nasdaq.com"
        )
    elif "weather" in query.lower():
        enhanced_query = f"{query} weather forecast"
    elif "news" in query.lower():
        enhanced_query = f"{query} latest news today"
    else:
        enhanced_query = query

    return search.run(enhanced_query)


search_tool = Tool(
    name="search",
    func=enhanced_search,
    description="search the web for current information including stock prices, news, weather, and other real-time data",
)
