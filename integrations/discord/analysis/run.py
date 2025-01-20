import os
import aiosqlite
import asyncio
from datetime import datetime
from pprint import pprint
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.agents import initialize_agent, Tool, AgentType
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# Set up OpenAI API Key
openai_api_key = os.environ.get("OPENAI_API_KEY")

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
1. Summarize the conversation, highlighting important topics and messages.
2. Extract key insights such as sentiment, trends, and any interesting observations.
3. Suggest possible actions based on the conversation, like follow-ups, actions for the team, or key decisions to make.

Provide your output in a structured format:
- **Summary**: A brief summary of the conversation.
- **Insights**: Key insights, such as trends, user sentiment, or important messages.
- **Actions**: Suggested actions for the team or relevant stakeholders.
"""

prompt = ChatPromptTemplate.from_template(template)

chain = prompt | llm | StrOutputParser()

async def get_messages_in_time_range(start_date: str, end_date: str, channel_id: int):
    start_timestamp = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
    end_timestamp = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')

    query = """
        SELECT m.content, m.timestamp, u.name
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.channel_id = ? AND m.timestamp BETWEEN ? AND ?
    """

    # Fetch messages from SQLite database
    async with aiosqlite.connect('saas_db.sqlite') as db:
        cursor = await db.cursor()
        await cursor.execute(query, (channel_id, start_timestamp, end_timestamp))
        result = await cursor.fetchall()

    return result

async def main():
    messages = await get_messages_in_time_range(start_date="2025-01-20 09:39:32", end_date="2025-01-20 12:39:32", channel_id=1)
    print(messages)
    pprint(chain.invoke({"messages": messages}))

asyncio.run(main())