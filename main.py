import os
import sys
import json
from datetime import datetime
from time import mktime
from urllib.parse import quote_plus

import feedparser
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables (OPENAI_API_KEY)
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Google News RSS locale settings per language
LANGUAGE_SETTINGS = {
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    "cs": {"hl": "cs", "gl": "CZ", "ceid": "CZ:cs"},
}


# Function Implementations
def search_news(query: str, language: str = "cs", max_results: int = 10):
    """Search Google News RSS and return the newest articles."""
    settings = LANGUAGE_SETTINGS.get(language, LANGUAGE_SETTINGS["cs"])
    max_results = max(1, min(int(max_results), 20))

    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}"
        f"&hl={settings['hl']}&gl={settings['gl']}&ceid={settings['ceid']}"
    )
    feed = feedparser.parse(url)

    if feed.bozo and not feed.entries:
        return {"query": query, "error": f"Failed to fetch news: {feed.bozo_exception}"}

    # Newest first
    entries = sorted(
        feed.entries,
        key=lambda e: e.get("published_parsed") or (0,) * 9,
        reverse=True,
    )

    articles = []
    for entry in entries[:max_results]:
        published = entry.get("published_parsed")
        articles.append(
            {
                "title": entry.get("title"),
                "source": entry.get("source", {}).get("title"),
                "published": (
                    datetime.fromtimestamp(mktime(published)).strftime("%Y-%m-%d %H:%M")
                    if published
                    else None
                ),
                "link": entry.get("link"),
            }
        )

    return {"query": query, "language": language, "count": len(articles), "articles": articles}


# Define custom tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": (
                "Search the latest news articles and announcements on any topic "
                "(e.g. AI, Databricks, Azure, tech, Czech economy or politics). "
                "Returns titles, sources, publish dates and links, newest first. "
                "Tip: append 'when:7d' (or when:1d, when:30d) to the query to limit the time range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'Databricks announcement when:7d' or 'česká ekonomika inflace'",
                    },
                    "language": {
                        "type": "string",
                        "enum": ["en", "cs"],
                        "description": "Language/region of the news: 'en' for English (US), 'cs' for Czech (CZ).",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of articles to return (1-20). Default 10.",
                    },
                },
                "required": ["query", "language"],
            },
        },
    },
]

available_functions = {
    "search_news": search_news,
}


# Agent loop: keeps calling the model until it stops requesting tools
def run_agent(messages, model="gpt-4o", max_iterations=5):
    for iteration in range(max_iterations):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message

        # No tool call -> final answer
        if not response_message.tool_calls:
            return response_message.content

        # Keep the assistant's tool-call message in history
        messages.append(response_message)

        # The model may request several tool calls at once (e.g. EN + CZ search)
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"[iteration {iteration + 1}] Tool call: {function_name}({function_args})")

            function_to_call = available_functions[function_name]
            function_response = function_to_call(**function_args)
            print(f"  -> {function_response.get('count', 0)} articles found")

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_response, ensure_ascii=False),
                }
            )

    return "Stopped: reached maximum number of iterations."


# Example usage: python main.py "What's new with Databricks this week?"
if __name__ == "__main__":
    question = (
        " ".join(sys.argv[1:])
        or "What are the latest announcements about Databricks and Azure AI this week?"
    )

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a helpful news assistant. Today is {datetime.now():%Y-%m-%d}. "
                "Use the search_news tool to find current information. "
                "Answer in the language of the user's question. "
                "Summarize the key points as short bullets and cite sources with links. "
                "List ALL relevant articles returned by the tool (not just a selection); "
                "merge duplicates covering the same story into one bullet with multiple sources."
            ),
        },
        {"role": "user", "content": question},
    ]

    print(f"Question: {question}\n")
    answer = run_agent(messages)
    print("\n--- Answer: ---")
    print(answer)
