# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import signal
import sys
from types import FrameType
from typing import Dict, List

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from starlette.status import HTTP_403_FORBIDDEN

from integrations.github_integrations.get import GitHubAnalytics
from utils.logging import logger

app = FastAPI(
    title="ContribuTrack Integrations",
    version="0.1.0",
    summary="API for ContribuTrack Integrations",
    description="API for ContribuTrack Integrations ; Currently supported : Github, Discord , Slack , Jira",
    contact={"name": "ContribuTrack", "email": "contributrack@gmail.com"},
)

tags_metadata = [
    {
        "name": "GitHub",
        "description": "Operations related to GitHub",
    },
    {
        "name": "Discord",
        "description": "Operations related to Discord",
    },
    {
        "name": "Slack",
        "description": "Operations related to Slack",
    },
    {
        "name": "Jira",
        "description": "Operations related to Jira",
    },
]


@app.get("/")
async def hello() -> str:
    # Use basic logging with custom fields
    logger.info(logField="custom-entry", arbitraryField="custom-entry")

    # https://cloud.google.com/run/docs/logging#correlate-logs
    logger.info("Child logger with trace Id.")

    return "Hello, World!"



API_KEY = os.getenv("APP_API_KEY")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


class GithubContributions_by_repo(BaseModel):
    repo_name: str
    start_date: str
    end_date: str


@app.get("/github_repos_users", tags=["GitHub"], response_model=Dict[str, List[str]])
async def github_repos_users(api_key: str = Security(api_key_header)) -> dict:
    """
    Returns dictionary of users and their repositories
    """
    if api_key == API_KEY:
        analyser = GitHubAnalytics()
        logger.info("Fetching repositories and users from GitHub")
        return analyser.get_users_repositories()
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")


@app.get("/github_repo_contributions", tags=["GitHub"], response_model=List[str])
async def github_repos_contributions(
    data: GithubContributions_by_repo, api_key: str = Security(api_key_header)
) -> List[str]:
    """
    Returns list of repositories and their contributions
    """
    if api_key == API_KEY:
        analyser = GitHubAnalytics()
        logger.info("Fetching repositories and contributions from GitHub")
        return analyser.get_repository_contributors(
            repo_name=data.repo_name, start_date=data.start_date, end_date=data.end_date
        )
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")


@app.get("/github_summary_repo", tags=["GitHub"], response_model=List[str])
async def github_summary_repo(
    data: GithubContributions_by_repo, api_key: str = Security(api_key_header)
) -> List[str]:
    """
    Returns summary of repository
    """
    if api_key == API_KEY:
        analyser = GitHubAnalytics()
        logger.info("Fetching summary of repository from GitHub")
        return analyser.analyze_contributions(
            repo_name=data.repo_name, start_date=data.start_date, end_date=data.end_date
        )
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")


@app.get("/github_codepatches", tags=["GitHub"], response_model=List[str])
async def github_codepatches(
    data: GithubContributions_by_repo, api_key: str = Security(api_key_header)
) -> List[str]:
    """
    Returns list of code patches
    """
    if api_key == API_KEY:
        analyser = GitHubAnalytics()
        logger.info("Fetching code patches from GitHub")
        return analyser.get_user_code_patches(
            repo_name=data.repo_name, start_date=data.start_date, end_date=data.end_date
        )
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")


@app.get("/github_user_activity", tags=["GitHub"], response_model=List[str])
async def github_user_activity(
    data: GithubContributions_by_repo, api_key: str = Security(api_key_header)
) -> List[str]:
    """
    Returns user activity
    """
    if api_key == API_KEY:
        analyser = GitHubAnalytics()
        logger.info("Fetching user activity from GitHub")
        return analyser.analyze_user_contributions(
            repo_name=data.repo_name, start_date=data.start_date, end_date=data.end_date
        )
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key")


def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")

    from utils.logging import flush

    flush()

    # Safely exit program
    sys.exit(0)


if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment
    import uvicorn

    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)

    uvicorn.run(app, host="localhost", port=8080)
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)
