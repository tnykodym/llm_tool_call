# LLM Tool Call – News Agent

A small demo of **OpenAI function calling (tool use)**. You ask a question in natural language, the model (`gpt-4o`) decides when to call the `search_news` tool, which fetches the latest articles from **Google News RSS**, and then it writes a short bulleted summary with links to the sources.

The agent loop in `main.py` keeps calling the model until it stops requesting tools (at most 5 iterations). The model may run several searches in one step, e.g. an English and a Czech search at the same time.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then put your key in OPENAI_API_KEY
```

## Usage

```bash
python main.py "What's new with Databricks this week?"
python main.py "Jaký je vývoj inflace v ČR?"
```

With no argument, a default question about Databricks and Azure AI is used. The answer comes back in the language of the question. The script prints each tool call and how many articles it found, then the final answer.

## `search_news` parameters

The model fills these in itself based on your question. You steer them through how you phrase the question.

| Parameter     | Required | Values                | Description |
|---------------|----------|-----------------------|-------------|
| `query`       | yes      | text                  | Search terms. Supports Google News operators, e.g. `when:1d`, `when:7d` or `when:30d` to limit the time range. |
| `language`    | yes      | `en`, `cs`            | `en` = English news (US), `cs` = Czech news (CZ). Unknown values fall back to `cs`. |
| `max_results` | no       | 1–20 (default 10)     | Maximum number of articles returned, newest first. |

Examples of questions that steer the parameters:

- *"Databricks news from the last 24 hours"* → `query: "Databricks when:1d"`
- *"Czech and English news about Azure AI this month"* → two calls, `language: "cs"` and `"en"`, with `when:30d`
- *"Give me the top 5 articles about OpenAI"* → `max_results: 5`

Each result contains the article `title`, `source`, `published` date (`YYYY-MM-DD HH:MM`) and `link`.
