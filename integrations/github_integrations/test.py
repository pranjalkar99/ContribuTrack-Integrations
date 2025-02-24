from datetime import datetime, timedelta

from dotenv import load_dotenv
from get import GitHubAnalytics
from langchain_community.agent_toolkits.github.toolkit import GitHubToolkit
from langchain_community.utilities.github import GitHubAPIWrapper
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

load_dotenv()


github = GitHubAPIWrapper()
toolkit = GitHubToolkit.from_github_api_wrapper(github)

tools = toolkit.get_tools()

for tool in tools:
    print(tool.name)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=1000,
    timeout=None,
)

tools = [tool for tool in toolkit.get_tools() if tool.name == "Search code"]
assert len(tools) == 1
tools[0].name = "search_code"

agent_executor = create_react_agent(llm, tools)

example_query = "summarize code changes in the last 3 months"

events = agent_executor.stream(
    {"messages": [("user", example_query)]},
    stream_mode="values",
)
for event in events:
    event["messages"][-1].pretty_print()


def test_github_analytics():
    # Initialize the analyzer
    analyzer = GitHubAnalytics()

    # Set date range for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Get and analyze contributions
    repo_name = "owner/repository"
    analysis = analyzer.analyze_contributions(
        repo_name=repo_name, start_date=start_date, end_date=end_date
    )

    # Print results
    print("=== Repository Analysis ===")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print("\nSummary:")
    print(f"Total Contributors: {analysis['summary']['total_contributors']}")
    print(f"Total Commits: {analysis['summary']['total_commits']}")
    print(f"Lines Added: {analysis['summary']['total_lines_added']}")
    print(f"Lines Deleted: {analysis['summary']['total_lines_deleted']}")

    print("\nDetailed Analysis:")
    print(analysis["analysis"])


if __name__ == "__main__":
    test_github_analytics()
