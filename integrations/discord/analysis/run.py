import asyncio
import json
import os
from datetime import datetime
from pprint import pprint

import aiosqlite
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

from integrations.jira.utils import create_jira_issue

load_dotenv()

# Set up OpenAI API Key
openai_api_key = os.environ.get("OPENAI_API_KEY")

# Use Local LLM , if data is sensitive

if os.environ.get("USE_LOCAL_LLM") == "True":

    if os.environ.get("OLLAMA_SETUP_DONE") == "True":
        llm = ChatOllama(
            model="llama3.2",
            temperature=0,
            # other params...
        )
    else:
        ## run the private_data.sh and then set the OLLAMA_SETUP_DONE to True

        raise Exception(
            "Please run the private_data.sh script to set up the local LLM."
        )

        ## write code to run the bash script


else:
    # Initialize the language model
    llm = ChatOpenAI(
        model="gpt-4",
        temperature=0,
        max_tokens=1000,
        timeout=None,
    )

template = """
system: You are a helpful assistant that summarizes conversations and extracts useful information.
human: 
You have the following messages from a Discord channel:

{messages}

Your task:
1. Summarize the conversation.
2. Extract key insights such as sentiment, trends, and observations.
3. Detect actionable tasks. For each task, include:
   - **Task Summary**
   - **Detailed Description**
   - **Priority** (High, Medium, Low)
   - **Due Date** (if applicable)

Respond in JSON format:
{{
  "summary": "...",
  "insights": "...",
  "actions": [
    {{
      "summary": "...",
      "description": "...",
      "priority": "...",
      "due_date": "..." 
    }}
  ]
}}
"""

prompt = ChatPromptTemplate.from_template(template)

chain = prompt | llm | StrOutputParser()


async def get_messages_in_time_range(start_date: str, end_date: str, channel_id: int):
    start_timestamp = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_timestamp = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

    query = """
        SELECT m.content, m.timestamp, u.name
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.channel_id = ? AND m.timestamp BETWEEN ? AND ?
    """

    # Fetch messages from SQLite database
    async with aiosqlite.connect("saas_db.sqlite") as db:
        cursor = await db.cursor()
        await cursor.execute(query, (channel_id, start_timestamp, end_timestamp))
        result = await cursor.fetchall()

    return result


async def main():
    messages = await get_messages_in_time_range(
        start_date="2025-01-20 09:39:32", end_date="2025-02-02 12:39:32", channel_id=1
    )

    output = chain.invoke({"messages": messages})
    pprint(output)

    output = json.loads(output)

    # Automatically create tasks if actions are detected
    actions = output.get("actions", [])
    for task in actions:
        pprint(task)
        create_jira_issue(task)


asyncio.run(main())
