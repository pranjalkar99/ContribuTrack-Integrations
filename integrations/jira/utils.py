import json
import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()


JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
API_ENDPOINT = f"{JIRA_BASE_URL}/rest/api/3/issue"
EMAIL = os.getenv("JIRA_API_EMAIL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT = os.getenv("JIRA_PROJECT")


def create_jira_issue(task):
    issue_data = {
        "fields": {
            "project": {"key": os.getenv("JIRA_PROJECT")},
            "summary": task["summary"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": task["description"]}],
                    }
                ],
            },
            "issuetype": {"name": "Task"},
            # "priority": {"name": task.get("priority", "Medium")},
            # "duedate": task.get("due_date", None),
        }
    }

    response = requests.post(
        API_ENDPOINT,
        data=json.dumps(issue_data),
        headers={"Content-Type": "application/json"},
        auth=HTTPBasicAuth(EMAIL, API_TOKEN),
    )

    if response.status_code == 201:
        print(f"✅ Task created: {response.json()['key']}")
    else:
        print(f"❌ Failed to create task: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    task = {
        "description": "pranjalkar99 asked everyone to help fix a server "
        "misconfiguration issue. This task was eventually completed.",
        "due_date": "2025-01-20 09:53:00",
        "priority": "High",
        "summary": "Fix server misconfiguration issue",
    }

    create_jira_issue(task)
