from github import Github, Auth
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from datetime import datetime, timedelta
import jwt
import time
import requests
from pprint import pprint
import sqlite3

load_dotenv()

class GitHubAnalytics:
    def __init__(self):
        # Initialize with GitHub App credentials
        self.github_app_id = os.getenv("GITHUB_APP_ID")
        self.github_private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
        self.github_installation_id = os.getenv("GITHUB_INSTALLATION_ID")
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID")
        
        # Initialize LangChain
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize GitHub client
        auth = self._get_github_app_token()
        self.github = Github(auth)

    def _get_github_app_token(self):
        """Get GitHub App installation access token"""
        # Generate JWT
        now = int(time.time())
        payload = {
            'iat': now,  # Issued at time
            'exp': now + (60 * 10),  # JWT expiration time (10 minutes)
            'iss': self.github_app_id  # GitHub App ID
        }
        # print("Payload: ", payload)
        jwt_token = jwt.encode(payload, self.github_private_key, algorithm='RS256')

        # print(jwt_token)

        # Request installation access token
        url = f"https://api.github.com/app/installations/{self.github_installation_id}/access_tokens"
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Accept': 'application/vnd.github+json',
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        response = requests.post(url, headers=headers)
        response_data = response.json()

        # pprint(response_data)
        
        if response.status_code == 201:
            return response_data['token']  # Return the installation access token
        else:
            raise Exception(f"Failed to obtain access token: {response_data.get('message', 'Unknown error')}")

    def get_repository_contributors(
        self, 
        repo_name: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get contributors and their contributions for a repository
        """
        repo = self.github.get_repo(repo_name)
        contributors = []

        # Ensure start_date and end_date are timezone-aware
        if start_date:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date:
            end_date = end_date.replace(tzinfo=timezone.utc)

        for contributor in repo.get_contributors():
            commits = repo.get_commits(author=contributor.login)
            
            contributor_data = {
                "login": contributor.login,
                "name": contributor.name if hasattr(contributor, 'name') else None,
                "email": contributor.email if hasattr(contributor, 'email') else None,
                "commits": [],
                "total_commits": 0,
                "lines_added": 0,
                "lines_deleted": 0
            }

            for commit in commits:
                commit_date = commit.commit.author.date
                
                # Ensure commit_date is timezone-aware
                if commit_date.tzinfo is None:
                    commit_date = commit_date.replace(tzinfo=timezone.utc)

                # Filter by date range if specified
                if start_date and commit_date < start_date:
                    continue
                if end_date and commit_date > end_date:
                    continue

                stats = commit.stats
                contributor_data["commits"].append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "date": commit_date,
                    "additions": stats.additions,
                    "deletions": stats.deletions,
                })
                contributor_data["total_commits"] += 1
                contributor_data["lines_added"] += stats.additions
                contributor_data["lines_deleted"] += stats.deletions

            if contributor_data["total_commits"] > 0:
                contributors.append(contributor_data)

        return contributors

    def analyze_contributions(
        self, 
        repo_name: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Analyze contributions and generate summaries using LangChain
        """
        contributors = self.get_repository_contributors(repo_name, start_date, end_date)
        
        # Create prompt template for contribution analysis
        prompt = ChatPromptTemplate.from_template("""
        Analyze the following GitHub contribution data and provide a detailed summary:
        
        Repository: {repo_name}
        Time Period: {time_period}
        
        Contribution Data:
        {contribution_data}
        
        Please provide:
        1. Overall activity summary
        2. Key contributors and their impact
        3. Notable trends or patterns
        4. Significant commits or changes
        """)
        
        # Create LangChain for analysis
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Format time period string
        time_period = f"{start_date.strftime('%Y-%m-%d') if start_date else 'beginning'} to {end_date.strftime('%Y-%m-%d') if end_date else 'present'}"
        
        # Format contribution data for analysis
        contribution_data = "\n".join([
            f"- {c['login']}: {c['total_commits']} commits, "
            f"+{c['lines_added']} -{c['lines_deleted']} lines"
            for c in contributors
        ])
        
        # Generate analysis
        analysis = chain.run({
            "repo_name": repo_name,
            "time_period": time_period,
            "contribution_data": contribution_data
        })
        
        return {
            "contributors": contributors,
            "analysis": analysis,
            "summary": {
                "total_contributors": len(contributors),
                "total_commits": sum(c["total_commits"] for c in contributors),
                "total_lines_added": sum(c["lines_added"] for c in contributors),
                "total_lines_deleted": sum(c["lines_deleted"] for c in contributors),
            }
        }

    def analyze_commit_messages(self, repo_name: str, commits: List[Dict]) -> str:
        """
        Analyze commit messages using LangChain to identify patterns and summarize changes
        """
        prompt = ChatPromptTemplate.from_template("""
        Analyze the following commit messages and provide a summary of the changes:
        
        Commits:
        {commit_messages}
        
        Please provide:
        1. Main types of changes
        2. Key features or improvements
        3. Bug fixes or issues addressed
        4. Overall development direction
        """)
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        commit_messages = "\n".join([
            f"- {commit['date'].strftime('%Y-%m-%d')}: {commit['message']}"
            for commit in commits
        ])
        
        return chain.run({
            "commit_messages": commit_messages
        })

    def get_user_code_patches(self, repo_name: str, username: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get all code patches for a specific user in a repository.
        """
        repo = self.github.get_repo(repo_name)
        patches = []

        for commit in repo.get_commits(author=username):
            commit_date = commit.commit.author.date
            
            # Ensure commit_date is timezone-aware
            if commit_date.tzinfo is None:
                commit_date = commit_date.replace(tzinfo=timezone.utc)

            # Ensure start_date and end_date are timezone-aware
            if start_date:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date:
                end_date = end_date.replace(tzinfo=timezone.utc)

            # Filter by date range if specified
            if start_date and commit_date < start_date:
                continue
            if end_date and commit_date > end_date:
                continue

            # Fetch commit details using the GitHub API
            url = f"https://api.github.com/repos/{repo.owner.login}/{repo.name}/commits/{commit.sha}"
            headers = {
                'Authorization': f'Bearer {self._get_github_app_token()}',
                'Accept': 'application/vnd.github.v3+json'
            }
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch commit details: {response.json().get('message', 'Unknown error')}")

            commit_details = response.json()
            patch = ""
            
            # Iterate through the files changed in the commit
            for file in commit_details.get('files', []):
                patch += f"File: {file['filename']}\n"
                patch += f"Status: {file['status']}\n"
                patch += f"Patch:\n{file.get('patch', 'No patch available')}\n\n"  # Access the patch for each file

            patches.append({
                "sha": commit.sha,
                "message": commit.commit.message,
                "date": commit_date,
                "patch": patch.strip()  # Remove any trailing whitespace
            })

        return patches

    def analyze_large_code_patches(self, code_patches: List[Dict]) -> str:
        """
        Analyze large code patches using LangChain to identify patterns and summarize changes.
        """
        prompt = ChatPromptTemplate.from_template(""" 
        Analyze the following code patches and provide a summary of the changes:
        
        Code Patches:
        {code_patches}
        
        Please provide:
        1. Main types of changes
        2. Key features or improvements
        3. Bug fixes or issues addressed
        4. Overall development direction
        """)
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Format code patches for analysis
        formatted_patches = "\n".join([f"- {patch['date'].strftime('%Y-%m-%d')}: {patch['message']}\n{patch['patch']}" for patch in code_patches])
        
        return chain.run({
            "code_patches": formatted_patches
        })

    def analyze_user_contributions(
        self, 
        username: str, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> None:
        """
        Check if the user has contributions in any accessible repositories,
        retrieve contributions, and save them in a SQLite database.
        """
        # Connect to SQLite database
        conn = sqlite3.connect('saas_db.sqlite')
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_contributions (
                repo_name TEXT,
                username TEXT,
                total_commits INTEGER,
                lines_added INTEGER,
                lines_deleted INTEGER,
                date TEXT
            )
        ''')

        # Use the GitHub API to get repositories accessible by the app
        installation_repos_url = f"https://api.github.com/installation/repositories"
        headers = {
            'Authorization': f'Bearer {self._get_github_app_token()}',
            'Accept': 'application/vnd.github+json'
        }
        response = requests.get(installation_repos_url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get repositories: {response.json().get('message', 'Unknown error')}")

        repos_data = response.json().get('repositories', [])

        print("Repos Data: ", repos_data)

        for repo in repos_data:
            repo_name = repo['full_name']  # Use the full name of the repository
            # Get contributions for the specified user
            contributions = self.get_repository_contributors(repo_name, start_date, end_date)
            user_contributions = next((c for c in contributions if c['login'] == username), None)

            if user_contributions:
                # Get user code patches
                code_patches = self.get_user_code_patches(repo_name, username, start_date, end_date)
                # Save contributions to the database
                cursor.execute(''' 
                    INSERT INTO user_contributions (repo_name, username, total_commits, lines_added, lines_deleted, date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (repo_name, username, user_contributions['total_commits'], user_contributions['lines_added'], user_contributions['lines_deleted'], datetime.now().strftime('%Y-%m-%d')))

                # Analyze contributions (you can call the analyze_contributions method if needed)
                analysis = self.analyze_contributions(repo_name, start_date, end_date)
                print(f"Analysis for {username} in {repo_name}: {analysis}")
                
                # Analyze large code patches
                if code_patches:
                    large_code_analysis = self.analyze_large_code_patches(code_patches)
                    print(f"Large Code Patches Analysis for {username} in {repo_name}: ")
                    pprint(large_code_analysis)

        # Commit changes and close the connection
        conn.commit()
        conn.close()

def test_github_analytics():
    # Initialize the analyzer
    analyzer = GitHubAnalytics()
    
    # Set date range for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=530)
    
    # Get and analyze contributions
    repo_name = os.getenv("GITHUB_REPOSITORY")
    # analysis = analyzer.analyze_contributions(
    #     repo_name=repo_name,
    #     start_date=start_date,
    #     end_date=end_date
    # )
    
    # # Print results
    # print("=== Repository Analysis ===")
    # print(f"Period: {start_date.date()} to {end_date.date()}")
    # print(f"\nSummary:")
    # print(f"Total Contributors: {analysis['summary']['total_contributors']}")
    # print(f"Total Commits: {analysis['summary']['total_commits']}")
    # print(f"Lines Added: {analysis['summary']['total_lines_added']}")
    # print(f"Lines Deleted: {analysis['summary']['total_lines_deleted']}")
    
    # print("\nDetailed Analysis:")
    # pprint(analysis['analysis'])

    # Test the new analyze_user_contributions method
    username = "samthakur587"  # Replace with a valid GitHub username for testing
    pprint(f"\n=== Analyzing Contributions for {username} ===")
    analyzer.analyze_user_contributions(username, start_date, end_date)

if __name__ == "__main__":
    test_github_analytics()
