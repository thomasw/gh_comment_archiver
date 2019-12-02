#!/usr/bin/env python
# type: ignore
from datetime import datetime, timedelta
import functools
from json import dumps
from pathlib import Path
import sys
from time import sleep

from github import Github, RateLimitExceededException

# Configuration
OAUTH_TOKEN = "your_gh_auth_token"
ORG = "org_name"
USER = "username"
IGNORE_USERS = ["a_list_of_users", "that_you", "want_to_ignore"]
OUTPUT = Path("./output")
START_DATE = None
# End Configuration

GH = Github(OAUTH_TOKEN)


def exclude_user_comments(raw_data_comments, users):
    return [c for c in raw_data_comments if c["user"]["login"] not in users]


def get_raw_issue_comments(issue):
    return [comment.raw_data for comment in issue.get_comments()]


def get_repo_name(issue):
    repo_url = issue.raw_data["repository_url"]
    _, _, name = repo_url.rpartition("https://api.github.com/repos/")
    return name


def get_issue_output_path(issue):
    repo_name = get_repo_name(issue)

    return OUTPUT / repo_name / str(issue.number)


def to_json(data):
    return dumps(data, sort_keys=True, indent=4)


def with_retries(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
                break
            except RateLimitExceededException:
                print(
                    f"\n[{datetime.now()}] Rate limit error. "
                    "Sleeping for 15 minutes."
                )
                sleep(timedelta(minutes=15).seconds)

    return wrapper


@with_retries
def archive_issue(issue):
    issue_directory = get_issue_output_path(issue)
    issue_data = to_json(issue.raw_data)
    comments = get_raw_issue_comments(issue)
    comments = exclude_user_comments(comments, IGNORE_USERS)
    comments_data = to_json(comments)

    # Don't download issues created by ignored users if they don't also have
    # not-ignored comments.
    if issue.user.login in IGNORE_USERS and not comments:
        return

    Path.mkdir(issue_directory, parents=True, exist_ok=True)

    with open(issue_directory / "issue.json", "w") as fp:
        fp.write(issue_data)

    if comments:
        with open(issue_directory / "comments.json", "w") as fp:
            fp.write(comments_data)


def get_user_issues(user, org, start_date=None):
    query = {"sort": "created", "order": "asc", "involves": USER, "org": ORG}

    if start_date:
        query["created"] = f">{start_date.isoformat()}"

    return GH.search_issues("", **query)


issues = get_user_issues(USER, ORG, start_date=START_DATE)
downloaded_count = 0
oldest = issues[0] if issues else None
latest = None

# totalCount is sometimes an incorrect value unless an element is accessed
# prior to accessing the totalCount value.
print(f"Downloading {issues.totalCount} issues.")

# Either the Github API or pygithub is preventing retrieving more than ~1020
# results per search query. To work around this, we track the last issue
# downloaded and we search again using the created date for that issue as the
# new start date. This process is repeated until there are no more search
# results.
while issues.totalCount > 0:
    for issue in issues:
        archive_issue(issue)

        latest = issue
        downloaded_count += 1

        sys.stdout.write(f"\r{downloaded_count} downloaded.")
        sys.stdout.flush()

    print()  # Adds a line break after the "downloaded" output.
    print(f"Issues created before {latest.created_at.isoformat()} downloaded.")

    issues = get_user_issues(USER, ORG, start_date=latest.created_at)

    print(f"Issues remaining: {issues.totalCount}")

if oldest and latest:
    print(
        f"\nDownload complete: {downloaded_count} downloaded from "
        f"{oldest.created_at} to {latest.created_at}."
    )
else:
    print("No issues found.")
